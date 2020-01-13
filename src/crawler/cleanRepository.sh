#!bin/sh
find . -type f ! \( -name "*cleanRepository.sh" -or -name "*.c" -or -name "*.h" -or -name "ABOUT.txt" \) -delete
find . -type d -empty -delete