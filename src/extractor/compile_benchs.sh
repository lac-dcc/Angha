#!/bin/bash
cc="clang"

timestamp() {
	date +"%Y-%m-%d__%H:%M:%S"
}

if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]
then
	echo "Usage: $0 <source_dir> <destination_dir> <csv_file>"
	echo "source_dir -> folder containing programs to be compiled."
	echo "destination_dir -> folder where LLVM bytecodes should be stored."
	echo "csv_file -> file to output csv summarizing the results"
	exit 1
fi

source_folder=$(readlink -f $1)
dest_folder=$(readlink -f $2)

if [ ! -d "$source_folder" ]
then
	echo "Source directory does not exist!"
	exit 1
fi

if [ ! -d "$dest_folder" ]
then
	mkdir $dest_folder
fi

csv_file=$3

echo "Source directory: $source_folder"
echo "Destination directory: $dest_folder"

echo "$(timestamp) ----- BEGINNING COMPILATION -----"
echo "benchmark,size,status" >>${csv_file}

files=$(find $source_folder -name "*.c")

for f in $files; do
	base=$(basename $f)
	no_ext=${base%.*}
	size=$(stat -c%s "${f}")

	echo "$(timestamp) Attempting to compile file: $base. Number of bytes: $size"

	$cc $f -S -emit-llvm -c -Xclang -disable-O0-optnone -o "${source_folder}/${no_ext}.bc"

	res=$?

	if [[ $res != 0 ]]
	then
		echo "${base},${size},FAIL" >>${csv_file}
	else
		echo "${base},${size},SUCCESS" >>${csv_file}
	fi
done

echo "$(timestamp) ----- FINISHED COMPILATION -----"
