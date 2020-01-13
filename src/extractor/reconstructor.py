import os
import sys
import shutil
import traceback

from datetime import datetime
import time

import multiprocessing as mp
import subprocess as sp

import tempfile
	
#Writes a timestamped log entry into a given log
def write_log(log, message):
	#don't log if logging is disabled
	if log_level < 1:
		return

	timestamp = datetime.now().strftime("[%d-%b-%Y (%H:%M:%S)]")
	log.append((timestamp,message))


def write_csv_entry(csv, entry):
	#don't log if advanced logging is disabled
	if (log_level < 2):
		return
	csv.append(entry)

#Dumps a csv entry log to an output stream
def dump_csv(csv, stream=sys.stdout):
	for entry in csv:
		print(entry, file=stream)

#Dumps a logs entries to an output stream
def dump_log(log, stream=sys.stdout):
	for entry in log:
		print(entry[0] + " " + entry[1], file=stream)

#Base error class
class Error(Exception):
	pass

#Simple error for when directories to be extracted are not found
class DirNotFoundError(Error):
	def __init__(self, directory):
		self.message = "Directory not found: " + directory

#Simple error to indicate when binaries are not found
class BinNotFoundError(Error):
	def __init__(self, binary_path):
		self.message = "Binary not found: " + binary_path

#Class responsible for performing code reconstruction. This implies going over
#a list of files, and attempting to reconstruct the code within them, then
#compile them to verify that they are compilable.
#Inputs:
#@root_dir -> root directory of a corpus of repositories, where each
#             subdirectory is a repository of extracted C code
#@compiler_path -> path to a compiler to verify program validity
#@psychec_path -> path to a PsycheC directory with the constraint generator and
#				  solver already built
#@dest_dir -> parent directory where the resulting programs should be stored
class Reconstructor:
	def __init__(self, root_dir, compiler_path, psychec_path, dest_dir):
		if not os.path.exists(os.path.abspath(root_dir)):
			raise DirNotFoundError(root_dir)
		self.root_dir = os.path.abspath(root_dir)

		self.compiler = shutil.which(compiler_path)
		if self.compiler == None:
			raise BinNotFoundError(compiler_path)

		if not os.path.exists(os.path.abspath(psychec_path)):
			raise DirNotFoundError(psychec_path)
		self.psychec_dir = os.path.abspath(psychec_path)

		psychecgen_path = os.path.join(self.psychec_dir, "psychecgen")
		self.psychecgen = shutil.which(psychecgen_path)
		if self.psychecgen == None:
			raise BinNotFoundError(psychecgen_path)

		solver_path = os.path.join(self.psychec_dir, "solver")
		if not os.path.exists(solver_path):
			raise DirNotFoundError(solver_path)
		self.solver_dir = os.path.abspath(solver_path)

		if not os.path.exists(os.path.abspath(dest_dir)):
			ans = None
			while (ans != 'y' and ans != 'n'):
				print("Destination directory does not exist. Create it? y/n")
				ans = input()
			if (ans == 'y'):
				try:
					os.makedirs(dest_dir)
				except OSError:
					print("Could not create destination directory!")
				else:
					print("Destination directory created successfully!")
			else:
				print("Fatal error, no destination directory!")
				sys.exit(1)
		self.dest_dir = os.path.abspath(dest_dir)

		self.num_files_processed = 0
		self.num_functions_generated_constraints = 0
		self.num_functions_reconstructed = 0
		self.num_timeouts = 0
		self.num_functions_compiled = 0

		self.exec_log = []

		self.recon_file_log = ["file,repo,status"]
		self.recon_repo_log = ["repo,con_gen,con_solved,timeouts,compiled"]

		write_log(self.exec_log, "---------- Reconstruction Settings ----------")
		write_log(self.exec_log, "Folder to reconstruct: " + self.root_dir)
		write_log(self.exec_log, "PsycheC constraint generator: " + self.psychecgen)
		write_log(self.exec_log, "Verification compiler: " + self.compiler)
		write_log(self.exec_log, "Destination directory: " + self.dest_dir)
		write_log(self.exec_log, "-----------------------------------------")

	#This function processes a single file, by performing all the steps in
	#the reconstruction pipeline. That is, generating constraints for the file,
	#then attempting to solve the constraints to reconstruct all the types. If
	#the process is successful, the generated types are embedded onto the
	#original file to make it compilable.
	def process_file(self, repo, f):
		gen_con = 0
		solved = 0
		timeout = 0
		compiled = 0

		#We create a temporary directory to avoid messing with the original
		#directory tree's structure	
		with tempfile.TemporaryDirectory(dir='/tmp') as dirname:
			#Set the arguments for psychecgen execution
			args = []
			args.extend([self.psychecgen, f])

			#Generate constraints
			p = sp.Popen(args, cwd=dirname)
			p.wait()
			
			#If constraints were not generated, bail out
			if (p.returncode != 0):
				return f, gen_con, timeout, solved, compiled
			gen_con = 1

			#Set the arguments for running the PsycheC solver
			con_file = os.path.join(dirname, "a.cstr")
			output_path = os.path.join(dirname, os.path.basename(f))
			args.clear()
			args.extend(["stack", "exec", "psychecsolver-exe", "--"])
			args.extend(["-i", con_file, "-o", output_path])

			#Run the solver with a timeout
			p = sp.Popen(args, cwd=self.solver_dir)
			try:
				p.communicate(timeout=5)
				p.wait()
			#On timeout return the result
			except sp.TimeoutExpired:
				p.kill()
				timeout = 1
				return f, gen_con, timeout, solved, compiled

			#Check if constraints were solved
			if (p.returncode != 0):
				return f, gen_con, timeout, solved, compiled
			solved = 1

			
			#Append original file to header
			with open(output_path, 'a') as outfile, open(f, 'r') as ori:
				outfile.write(ori.read())

			#Run compiler to verify if reconstructed function compiles
			args.clear()
			args.extend([self.compiler, "-c", "-fsyntax-only", output_path])

			p = sp.Popen(args, cwd=dirname)
			p.wait()

			#Check if file compiled successfully
			if (p.returncode != 0):
				return f, gen_con, timeout, solved, compiled
			compiled = 1

			#Get the path for the destination directory
			ori_dir = os.path.dirname(os.path.relpath(f, self.root_dir))
			new_dir = os.path.join(self.dest_dir, ori_dir)		

			#Create dir if it did not exist, then copy the output file
			if not os.path.exists(new_dir):
				os.makedirs(new_dir)
			shutil.copy2(output_path, new_dir)

		return f, gen_con, timeout, solved, compiled

	#function to reconstruct a single repository's directory. It traverses the
	#directory and its subdirectories in a top-down fashion, and attempts to
	#reconstruct types for each C file found.
	def reconstruct_repo(self, repo):
		write_log(self.exec_log, "Beginning reconstruction of repository: "
																	 + repo)
		num_repo_compiled = 0
		num_repo_const_gen = 0
		num_repo_con_solved = 0
		num_repo_timeouts = 0

		#Nested function to accumulate number of functions extracted
		def log_file_result(result):
			nonlocal repo, num_repo_compiled, num_repo_const_gen
			nonlocal num_repo_con_solved, num_repo_timeouts

			#grab the result from the subprocess function
			(f, gen_con, timeout, solved, compiled) = result

			basef = os.path.basename(f)
			num_repo_compiled += compiled
			num_repo_const_gen += gen_con
			num_repo_con_solved += solved
			num_repo_timeouts += timeout

			if (compiled == 1):
				status = "COMPILED"
			elif (timeout == 1):
				status = "TIMEOUT"
			elif (solved == 0 and gen_con == 1):
				status = "FAIL_SOLVE"
			else:
				status = "FAIL_GEN"

			write_csv_entry(self.recon_file_log, f+","+repo+","+status)

		#Nested function to handle exceptions within pool subprocesses
		def handle_error(e):
			traceback.print_exception(type(e), e, e.__traceback__)

		pool = mp.Pool(mp.cpu_count())

		#Find C source files and start a subprocess to reconstruct each
		fullpath = os.path.join(self.root_dir, repo)
		dir_tree = os.walk(fullpath)
		for (root, dirs, files) in dir_tree:
			for f in files:
				if not f.endswith(".c"):
					continue
				write_log(self.exec_log,"{" + repo + "} Processing file: "+ f)
				pool.apply_async(self.process_file, args=(repo, root+"/"+f),
						callback=log_file_result, error_callback=handle_error)
				self.num_files_processed += 1

		pool.close()
		pool.join()

		write_log(self.exec_log,"Finished reconstruction of repository: "+repo)
		write_log(self.exec_log,"--------------------------------------")

		self.num_functions_compiled += num_repo_compiled
		self.num_functions_generated_constraints += num_repo_const_gen
		self.num_functions_reconstructed += num_repo_con_solved
		self.num_timeouts += num_repo_timeouts

		write_csv_entry(self.recon_repo_log,repo+','+str(num_repo_const_gen)+
					','+str(num_repo_con_solved)+','+str(num_repo_timeouts)+','
					+str(num_repo_compiled))

	#Performs the reconstruction  process, given the input root directory.
	def reconstruct(self):
		begin_time = time.time()

		#First level of subdir tree should be made up of separate repos.
		dir_list = os.listdir(self.root_dir)
		write_log(self.exec_log, "Repo folders to be reconstructed: " + 
																str(dir_list))
		write_log(self.exec_log, "------------------------------------")

		for repo in dir_list:
			self.reconstruct_repo(repo)

		end_time = time.time()

		self.time_elapsed = end_time - begin_time

	def report(self):
		write_log(self.exec_log, "Finished reconstruction process!")
		write_log(self.exec_log, "-------- Reconstruction report: --------")
		write_log(self.exec_log, "Number of files processed: "
											+ str(self.num_files_processed))
		write_log(self.exec_log, "Number of functions for which constraints "
								+ "were successfully generated: "
								+str(self.num_functions_generated_constraints))
		write_log(self.exec_log, "Number of functions which were successfully "
								+ "were reconstructed: " 
								+ str(self.num_functions_reconstructed))
		write_log(self.exec_log, "Number of timeouts while constraint solving: "
								+ str(self.num_timeouts))
		write_log(self.exec_log, "Number of functions succesfully compiled: "
								+ str(self.num_functions_compiled))
		write_log(self.exec_log, "Total time elapsed during reconstruction: "
							+ "{:.2f}".format(self.time_elapsed) + " seconds.")
		write_log(self.exec_log, "------------------------------------")

		if (log_level >= 1):
			with open("reconstruction.log", "w+") as fd:
				dump_log(self.exec_log, fd)

		if (log_level >= 2):
			with open("recon_file_log.csv", "w+") as fd:
				dump_csv(self.recon_file_log, fd)

			with open("recon_repo_log.csv", "w+") as fd:
				dump_csv(self.recon_repo_log, fd)

if __name__ == "__main__":
	global log_level

	if (len(sys.argv) < 5):
		print("Usage: ", sys.argv[0], '<repo_dir> <compiler_path>'
		' <psychec_path> <dest_dir> [log_level]')
		sys.exit(1)

	log_level = 1
	if (len(sys.argv) > 5):
		log_level = int(sys.argv[5])

	if (log_level < 0 or log_level > 2):
		print("Logging level choices are 0, 1 or 2!")
		sys.exit(1)

	reconstructor = Reconstructor(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
	reconstructor.reconstruct()
	reconstructor.report()
	dump_log(reconstructor.exec_log)
