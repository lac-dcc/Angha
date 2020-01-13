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

#Class responsible for performing code extraction. This can be either
#extracting code on a function-by-function basis or a file-by-file basis.
#Inputs:
#@root_dir -> root directory of a corpus of repositories, where each
#             subdirectory is a repository of C code
#@clang_path -> path to a clang binary compatible with the FunctionExtractor
#               plugin
#@extr_lib_path -> path to the shared library file for the FunctionExtractor
#                  plugin
#@dest_dir -> parent directory where the resulting programs should be stored
class Extractor:
	def __init__(self, root_dir, clang_path, extr_lib_path, dest_dir):

		#check if root directory to be extracted exists
		if not os.path.exists(os.path.abspath(root_dir)):
			raise DirNotFoundError(root_dir)
		self.root_dir = os.path.abspath(root_dir)

		#find clang binary
		self.clang = shutil.which(clang_path)
		if self.clang == None:
			raise BinNotFoundError(clang_path)

		#find FunctionExtractor plugin shared library
		if not os.path.isfile(os.path.abspath(extr_lib_path)):
			raise FileNotFoundError(extr_lib_path)
		self.extr_lib = os.path.abspath(extr_lib_path)

		#check for destination dir, prompt to create it if not existent
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

		#These are only used for log_level >=1
		self.exec_log = []

		self.num_functions_extracted = 0
		self.num_files_processed = 0

		write_log(self.exec_log, "---------- Extraction Settings ----------")
		write_log(self.exec_log, "Folder to extract: " + self.root_dir)
		write_log(self.exec_log, "Path to Clang: " + self.clang)
		write_log(self.exec_log, "Path to FunctionExtractor library: " + self.extr_lib)
		write_log(self.exec_log, "Destination directory: " + self.dest_dir)
		write_log(self.exec_log, "-----------------------------------------")

		#These are only used for log_level >= 2
		self.extr_file_log = ["file,repo,num_functions"]
		self.extr_repo_log = ["repo,num_functions"]

	#This function processes a single file, by performing all the steps in
	#the extraction pipeline. That is, extracting all function definitions from
	#it using the Clang plugin, then saving all the output function files to
	#the destination directory.
	def process_file(self, repo, f):
		num_functions = 0

		#We create a temporary directory to avoid messing with the original
		#directory tree's structure	
		with tempfile.TemporaryDirectory(dir='/tmp') as dirname:
			#Set the arguments for the clang execution
			args = []
			args.extend([self.clang, f, '-Xclang', '-load', '-Xclang'])
			args.extend([self.extr_lib, '-Xclang', '-add-plugin'])
			args.extend(['-Xclang', 'extract-funcs', '-fsyntax-only'])

			#Run clang with the extraction plugin
			p = sp.Popen(args, cwd=dirname)
			p.wait()

			#The number of functions extracted equals the number of files
			num_functions = len(os.listdir(dirname))

			#Get the path for the destination directory
			ori_dir = os.path.dirname(os.path.relpath(f, self.root_dir))
			new_dir = os.path.join(self.dest_dir, ori_dir)

			#Create dir if it did not exist, then copy files
			if not os.path.exists(new_dir):
				os.makedirs(new_dir)		

			for f in os.listdir(dirname):
				shutil.copy2(os.path.join(dirname, f), new_dir)

		return f, num_functions

	#function to extract a single repository's directory. It traverses the
	#directory and its subdirectories in a top-down fashion, and extracts code
	#from every C file found.
	def extract_repo(self, repo):
		write_log(self.exec_log, "Beginning extraction of repository: " + repo)
		num_repo_functions = 0

		#Nested function to accumulate number of functions extracted
		def log_file_result(result):
			nonlocal repo, num_repo_functions

			#grab the result from the subprocess function
			(f, num_functions_extracted) = result

			basef = os.path.basename(f)
			num_repo_functions += num_functions_extracted
			write_csv_entry(self.extr_file_log, basef + "," + repo + ","
							+ str(num_functions_extracted)) 

		#Nested function to handle exceptions within pool subprocesses
		def handle_error(e):
			traceback.print_exception(type(e), e, e.__traceback__)

		pool = mp.Pool(mp.cpu_count())

		#Find C source files and start a subprocess to extract each
		fullpath = os.path.join(self.root_dir, repo)
		dir_tree = os.walk(fullpath)
		for (root, dirs, files) in dir_tree:
			for f in files:
				if not f.endswith(".c"):
					continue
				write_log(self.exec_log,"{"+repo+"} Processing file: "+f)
				pool.apply_async(self.process_file, args=(repo, root+"/"+f),
						callback=log_file_result, error_callback=handle_error)
				self.num_files_processed += 1

		pool.close()
		pool.join()

		write_log(self.exec_log,"Finished extraction of repository: "+repo)
		write_log(self.exec_log,"--------------------------------------")
		self.num_functions_extracted += num_repo_functions

		write_csv_entry(self.extr_repo_log,repo+','+str(num_repo_functions))

	#Performs the extraction process, given the input root directory.
	def extract(self):
		begin_time = time.time()

		#First level of subdir tree should be made up of separate repos.
		dir_list = os.listdir(self.root_dir)
		write_log(self.exec_log, "Repo folders to be extracted: " + 
																str(dir_list))
		write_log(self.exec_log, "------------------------------------")

		for repo in dir_list:
			self.extract_repo(repo)

		end_time = time.time()

		self.time_elapsed = end_time - begin_time


	def report(self):
		write_log(self.exec_log, "Finished extraction process!")
		write_log(self.exec_log, "-------- Extraction report: --------")
		write_log(self.exec_log, "Number of files processed: "
											+ str(self.num_files_processed))
		write_log(self.exec_log, "Number of functions : "
										+ str(self.num_functions_extracted))
		write_log(self.exec_log, "Total time elapsed during extraction: "
							+ "{:.2f}".format(self.time_elapsed) + " seconds.")
		write_log(self.exec_log, "------------------------------------")

		if (log_level >= 1):
			with open("extraction.log", "w+") as fd:
				dump_log(self.exec_log, fd)

		if (log_level >= 2):
			with open("extr_file_log.csv", "w+") as fd:
				dump_csv(self.extr_file_log, fd)

			with open("extr_repo_log.csv", "w+") as fd:
				dump_csv(self.extr_repo_log, fd)

if __name__ == "__main__":
	global log_level

	if (len(sys.argv) < 5):
		print("Usage: ", sys.argv[0], '<repo_dir> <clang_path>'
		' <lib_path> <dest_dir> [log_level]')
		sys.exit(1)

	log_level = 1
	if (len(sys.argv) > 5):
		log_level = int(sys.argv[5])

	if (log_level < 0 or log_level > 2):
		print("Logging level choices are 0, 1 or 2!")
		sys.exit(1)

	extractor = Extractor(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
	extractor.extract()
	extractor.report()
	dump_log(extractor.exec_log)
