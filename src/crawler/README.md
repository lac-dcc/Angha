# Repository Crawler

The Repository Crawler is a JAVA application for mining programs from the GitHub open-source code host.
It builds a list of repositories written in C and sorts it by popularity, i.e.,
by the GitHub stars amount. The user defines the number of repositories to be cloned (the length of the list).
For each repository cloned, it is created a file ABOUT.txt containing some informations for the user:

- The original repository link
- Date in which it was cloned
- Number of source code files from 

To use Repository Crawler you will need to have JAVA JDK (version 1.8 or higher) installed. 

IMPORTANT: if you are intend to use Repository Crawler on a JAVA IDE, do not forget to add the two libraries provided in
your project.

```
  cd <path-to-this-repository>
  cd src/crawler/
  
  #compile Repository Crawler
  javac -classpath .:jcabi-github-0.41-jar-with-dependencies.jar:org.eclipse.jgit-5.3.0.201903130848-r.jar RepositoryMiner.java
  
  #run Repository Crawler
  java -classpath .:jcabi-github-0.41-jar-with-dependencies.jar:org.eclipse.jgit-5.3.0.201903130848-r.jar RepositoryMiner
```

After running, the cloned repositores are saved on the directory "cloned_repos/repos".

Usually, big projects repositories contain a lot of files of various types, so in order to delete anything that will not be 
useful, run the cleanRepository script. It will recursively delete all the cloned files which are not C source, header
files or the ABOUT.txt file. 

```
 cd <path-to-this-repository>
 cd src/crawler/
 mv cleanRepository.sh ./cloned_repos
 cd cloned_repos/
 chmod +x cleanRepository.sh
 sh cleanRepository.sh
 
 ```