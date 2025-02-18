import os
import json
import subprocess
import pandas as pd
import sys
import shutil
import re

class MASMAutograder:
    def __init__(self):
        self.dosbox_path = "/usr/bin/dosbox"
        self.masm_dir = "/home/cloudcompute/Documents/TAship/MASM11"  # update with your MASM directory
        self.masm_bin = os.path.join(self.masm_dir, "BIN")
        self.df = pd.DataFrame(columns=["student_id", "marks_awarded", "comments"])
        
    def add_entry(self, student_id, marks_awarded, comments):
        new_entry = pd.DataFrame({
            'student_id': [student_id],
            'marks_awarded': [marks_awarded],
            'comments': [comments]
        })
        self.df = pd.concat([self.df, new_entry], ignore_index=True)

    def get_short_name(self, filename):
        """Convert long filename to 8.3 DOS format"""
        # remove extension first
        name = os.path.splitext(filename)[0]
        ext = os.path.splitext(filename)[1]
        
        if len(name) > 8:
            # keep first 6 chars and add ~1
            name = name[:6] + "~1"
        
        # return with extension
        return name + ext
    

    def compile_asm(self, asm_file):
        try:
            # copy ASM file from current directory
            asm_filename = os.path.basename(asm_file)
            short_name = self.get_short_name(asm_filename)  # Get 8.3 format name
            bin_asm_path = os.path.join(self.masm_bin, asm_filename)
            shutil.copy2(asm_file, bin_asm_path)
            
            # create batch file with short filename
            batch_content = [
                f"masm {short_name};",  # use short name
                f"link {os.path.splitext(short_name)[0]}.obj;;;;",  # use short name
                "exit"
            ]
            
            # batch file 
            batch_path = os.path.join(self.masm_bin, "compile.bat")
            with open(batch_path, 'w') as f:
                f.write('\n'.join(batch_content))
            
            # dosbox commands
            dosbox_commands = [
                f"mount C: {self.masm_dir}",
                "C:",
                "cd BIN",
                "compile.bat",
                "exit"
            ]
            
            command_str = ""
            for cmd in dosbox_commands:
                command_str += f' -c "{cmd}"'
                
            print(f"Running DOSBox commands: {command_str}")
            
            # run dosbox with more verbose output
            process = subprocess.Popen(
                f"{self.dosbox_path} -conf /dev/null {command_str}",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # capture and print output in real-time
            while True:
                output = process.stdout.readline()
                if output:
                    print("DOSBox Output:", output.strip())
                if process.poll() is not None:
                    break
            
            stdout, stderr = process.communicate()
            
            if stderr:
                print("DOSBox Errors:", stderr)
                
            # check if files were created using short name
            short_basename = os.path.splitext(short_name)[0]
            obj_file = os.path.join(self.masm_bin, f"{short_basename}.OBJ")
            exe_file = os.path.join(self.masm_bin, f"{short_basename}.EXE")
            
            print(f"Checking for OBJ file: {obj_file}")
            print(f"OBJ file exists: {os.path.exists(obj_file)}")
            print(f"Checking for EXE file: {exe_file}")
            print(f"EXE file exists: {os.path.exists(exe_file)}")
                
            if os.path.exists(exe_file):
                return True, "Compilation successful"
            else:
                return False, "Compilation failed - no executable produced"
                
        except subprocess.TimeoutExpired:
            process.kill()
            return False, "Compilation timeout"
        except Exception as e:
            return False, f"Compilation error: {str(e)}"
        finally:
            # cleanup
            try:
                os.remove(bin_asm_path)
                os.remove(obj_file)
                os.remove(batch_path) 
            except:
                pass

    def run_test(self, original_asm_file, input_data):
        """Runs a single test case and captures console output"""
        try:
            # get the short filename for the EXE
            original_name = os.path.basename(original_asm_file)
            short_name = self.get_short_name(original_name)
            exe_filename = f"{os.path.splitext(short_name)[0]}.EXE"
            exe_path = os.path.join(self.masm_bin, exe_filename)

            print(f"[DEBUG] Testing EXE: {exe_path}")
            if not os.path.exists(exe_path):
                print(f"[ERROR] Executable not found: {exe_path}")
                return False, "Executable not found"

            # create a batch file with proper I/O redirection
            batch_path = os.path.join(self.masm_bin, "test.bat")
            with open(batch_path, 'w', newline='\r\n') as f:  # DOS-style line endings
                f.write("@echo off\n")
                f.write(f"{exe_filename} < script.txt > output.txt\n")
                f.write("exit\n")

            # create input script with DOS line endings
            script_path = os.path.join(self.masm_bin, "script.txt")
            with open(script_path, 'w', newline='\r\n') as f:
                f.write(str(input_data) + "\r\n")  # Add proper DOS newline

            # run dosbox with explicit output handling
            cmd = [
                self.dosbox_path,
                "-conf", "/dev/null",
                "-c", f"mount C {self.masm_dir}",
                "-c", "C:",
                "-c", "cd BIN",
                "-c", "test.bat",
                "-c", "exit"
            ]

            print(f"[DEBUG] Running command: {' '.join(cmd)}")
            
            # execute with timeout
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=15,
                text=True
            )

            # logging
            print(f"[DEBUG] DOSBox exit code: {process.returncode}")
            if process.stderr:
                print(f"[ERROR] DOSBox errors:\n{process.stderr[:500]}")

            # read program output from redirected file
            output_file = os.path.join(self.masm_bin, "OUTPUT.TXT")
            if os.path.exists(output_file):
                with open(output_file, 'r') as f:
                    raw_output = f.read()
                print(f"[DEBUG] Raw output from file ({len(raw_output)} chars):\n{raw_output[:200]}...")
            else:
                raw_output = ""
                print("[WARNING] OUTPUT.TXT not found")

            # clean up temporary files
            for fpath in [batch_path, script_path, output_file]:
                try:
                    os.remove(fpath)
                except:
                    pass

            return True, raw_output

        except subprocess.TimeoutExpired:
            return False, "Test execution timeout"
        except Exception as e:
            print(f"[ERROR] Exception: {str(e)}")
            return False, f"Test execution error: {str(e)}"

    def clean_output(self, output):
        """Cleans the program output with multiple normalization steps"""
        # convert to uppercase for case-insensitive comparison
        cleaned = output.upper()
        
        # remove DOS-specific characters and extra whitespace
        cleaned = cleaned.replace('\r', '')  # Remove carriage returns
        cleaned = cleaned.replace('\x1a', '')  # Remove DOS EOF character
        
        # normalize line endings and trim whitespace
        cleaned = '\n'.join([line.strip() for line in cleaned.split('\n')])
        
        # remove empty lines and duplicate spaces
        cleaned = '\n'.join(
            [' '.join(line.split()) 
            for line in cleaned.split('\n') 
            if line.strip()]
        ).strip()
        
        return cleaned

    def extract_student_id(self, filename):
        """Extract student ID from filename like 'Q1_2023A7PS0334G.asm'"""
        # regular expression to find ID pattern (assuming IDs like 2023A7PS0334G)
        match = re.search(r'(\d{4}[A-Z]\d[A-Z]{2}\d{4}[A-Z])', filename)
        if match:
            return match.group(1)
        # if no match, just return filename without extension
        return os.path.splitext(filename)[0]




    def grade_submission(self, asm_file, testcases):
        """Grades a single student submission"""
        marks_awarded = 0
        comments = []
        
        # first try to compile
        compile_success, compile_msg = self.compile_asm(asm_file)
        if not compile_success:
            comments.append(f"Compilation failed: {compile_msg}")
            return 0, "; ".join(comments)
            
        # run each test case
        for test_num, testcase in enumerate(testcases, 1):
            test_success, output = self.run_test(asm_file, testcase['input'])
            
            if not test_success:
                comments.append(f"Test {test_num} failed: {output}")
                continue
                
            actual_output = self.clean_output(output)
            expected_output = testcase['expected_output']
            
            if actual_output == expected_output:
                marks_awarded += testcase['marks']
                comments.append(f"Test {test_num} passed")
            else:
                comments.append(f"Test {test_num} failed: Expected '{expected_output}', got '{actual_output}'")
        
        # cleanup EXE file after all tests
        exe_base = os.path.splitext(self.get_short_name(os.path.basename(asm_file)))[0]
        exe_path = os.path.join(self.masm_bin, f"{exe_base}.EXE")
        if os.path.exists(exe_path):
            try:
                os.remove(exe_path)
                print(f"Cleaned up EXE: {exe_path}")
            except Exception as e:
                print(f"Error removing EXE: {str(e)}")
                
        return marks_awarded, "; ".join(comments)

    def grade_all_submissions(self, submissions_dir, testcases_file):
        """Grades all submissions in a directory"""
        # load testcases
        with open(testcases_file, 'r') as f:
            testcases = json.load(f)
            
        # process all subdirectories
        for root, dirs, files in os.walk(submissions_dir):
            for file in files:
                if file.endswith(('.asm', '.ASM')):
                    asm_file = os.path.join(root, file)
                    student_id = self.extract_student_id(file)
                    
                    print(f"Grading submission: {asm_file}")
                    print(f"Student ID: {student_id}")
                    
                    marks, comments = self.grade_submission(asm_file, testcases)
                    self.add_entry(student_id, marks, comments)
                    
        # save results
        self.df.to_csv('grading_results.csv', index=False)
        print(f"Grading complete! Results saved to grading_results.csv")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python masm_autograder.py <submissions directory> <testcases.json>")
        sys.exit(1)
        
    grader = MASMAutograder()
    grader.grade_all_submissions(sys.argv[1], sys.argv[2])