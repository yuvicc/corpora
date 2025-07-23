import subprocess
import argparse
import sys
import os
import shutil
from pathlib import Path

def test_single_input(fuzz_target, binary_path, input_file):
    """Test a single input file with bitcoinfuzz."""
    command = f"FUZZ={fuzz_target} {binary_path} {input_file}"
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout per file
        )
        
        # LibFuzzer typically returns 0 for successful runs (no crash)
        # Non-zero return codes usually indicate crashes or errors
        return result.returncode == 0, result.stdout, result.stderr
        
    except subprocess.TimeoutExpired:
        print(f"Timeout testing {input_file}")
        return False, "", "Timeout"
    except Exception as e:
        print(f"Error testing {input_file}: {e}")
        return False, "", str(e)

def process_corpora(fuzz_target, binary_path, corpora_path, output_folder):
    """Process all files in corpora folder and move non-crashing ones."""
    corpora_dir = Path(corpora_path)
    output_dir = Path(output_folder)
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all files in corpora directory
    input_files = []
    for item in corpora_dir.iterdir():
        if item.is_file():
            input_files.append(item)
    
    if not input_files:
        print(f"No files found in {corpora_path}")
        return
    
    print(f"Found {len(input_files)} files to test")
    print(f"Output folder: {output_dir}")
    print("-" * 50)
    
    successful_count = 0
    crashed_count = 0
    
    for i, input_file in enumerate(input_files, 1):
        print(f"[{i}/{len(input_files)}] Testing {input_file.name}...", end=" ")
        
        success, stdout, stderr = test_single_input(fuzz_target, binary_path, str(input_file))
        
        if success:
            print("✓ PASS")
            # Copy file to output folder
            try:
                shutil.copy2(input_file, output_dir / input_file.name)
                successful_count += 1
            except Exception as e:
                print(f"Error copying {input_file.name}: {e}")
        else:
            print("✗ CRASH/ERROR")
            crashed_count += 1
            # Optionally log crash details
            print(stderr)
            if stderr and "ERROR" in stderr or "CRASH" in stderr:
                print(f"    Crash details: {stderr.strip()[:100]}...")
    
    print("-" * 50)
    print(f"Results:")
    print(f"  Successful (non-crashing): {successful_count}")
    print(f"  Crashed/Failed: {crashed_count}")
    print(f"  Total processed: {len(input_files)}")
    print(f"  Non-crashing inputs saved to: {output_dir}")

def main():
    parser = argparse.ArgumentParser(
        description="Test bitcoinfuzz inputs individually and save non-crashing ones",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python bitcoinfuzz_filter.py psbt_parse ./bitcoinfuzz /path/to/corpora/psbt_parse ./filtered_inputs
  python bitcoinfuzz_filter.py tx_parse ./bitcoinfuzz /path/to/corpora/tx_parse ./safe_inputs
        """
    )
    
    parser.add_argument(
        "fuzz_target",
        help="Name of the fuzz target (e.g., psbt_parse, tx_parse)"
    )
    
    parser.add_argument(
        "binary_path",
        help="Path to the bitcoinfuzz binary (e.g., ./bitcoinfuzz)"
    )
    
    parser.add_argument(
        "corpora_path",
        help="Path to the corpora folder containing input files"
    )
    
    parser.add_argument(
        "output_folder",
        help="Path to folder where non-crashing inputs will be saved"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output for each test"
    )
    
    args = parser.parse_args()
    
    # Validate paths
    if not os.path.exists(args.binary_path):
        print(f"Error: Binary not found at {args.binary_path}")
        sys.exit(1)
    
    if not os.path.exists(args.corpora_path):
        print(f"Error: Corpora folder not found at {args.corpora_path}")
        sys.exit(1)
    
    print(f"Filtering bitcoinfuzz inputs:")
    print(f"  Fuzz target: {args.fuzz_target}")
    print(f"  Binary path: {args.binary_path}")
    print(f"  Corpora path: {args.corpora_path}")
    print(f"  Output folder: {args.output_folder}")
    print("-" * 50)
    
    try:
        process_corpora(
            args.fuzz_target,
            args.binary_path,
            args.corpora_path,
            args.output_folder
        )
    except KeyboardInterrupt:
        print("\nOperation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
