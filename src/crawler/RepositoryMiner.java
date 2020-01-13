/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */

import java.io.File;
import java.io.IOException;
import java.util.Iterator;
import java.util.List;

import javax.json.JsonObject;

import org.eclipse.jgit.api.Git;

import com.jcabi.github.Github;
import com.jcabi.github.Repo;
import com.jcabi.github.RtGithub;
import com.jcabi.github.Search.Order;
import java.nio.charset.Charset;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.text.SimpleDateFormat;
import java.util.Arrays;
import java.util.Date;
import org.apache.commons.io.FileUtils;



/**
 *
 * @author jw
 */
public class RepositoryMiner {

    /**
     * @param args the command line arguments
     */
    public static void main(String[] args) throws Exception {
    int count = 0;
    try {
      Github github = new RtGithub("asergufmg", "aserg.ufmg2009");
      String baseFolder = "cloned_repos/repos";

      // Search for C projects descending sorted by GitHub stars 
      Iterator<Repo> repos = github.search().repos("language:C", "stars", Order.DESC).iterator();
      while (repos.hasNext() && count < 9) {
        Repo repo = repos.next();
        JsonObject repoData = repo.json();
       
        String name = repoData.getString("name");
        String cloneUrl = repoData.getString("clone_url");
        System.out.println(cloneUrl);
        File folder = new File(baseFolder + "/" + name);
        cloneRepository(folder, cloneUrl);
        
        //Information about the repository:
        //Original link;
        //Data in which was downloaded
        //Number of C files
        String[] extension = new String[] {"c"};
        List<File> files = (List<File>) FileUtils.listFiles(folder, extension, true);
        File about = new File(baseFolder + "/" + name + "/ABOUT.txt");
        about.createNewFile();
        SimpleDateFormat formatter= new SimpleDateFormat("yyyy-MM-dd 'at' HH:mm:ss z");  
        Date date = new Date(System.currentTimeMillis());
        List<String> repInformation = Arrays.asList("Repository link:",cloneUrl, "Date in which was downloaded: ", formatter.format(date), "Number of C files: ", Integer.toString(files.size()));
        Path path = Paths.get(baseFolder + "/" + name + "/ABOUT.txt");
        Files.write(path, repInformation, Charset.forName("UTF-8"));
        System.out.println("Repository cloned at " + folder.toString());
        System.out.println("Number of C files: " + files.size());
        files.clear();
        count++;
      }
    } catch (IOException e) {
      throw new RuntimeException(e);
    }

  }

  static void cloneRepository(File folder, String cloneUrl) throws Exception {
    Git.cloneRepository().setDirectory(folder).setURI(cloneUrl).setCloneAllBranches(false).call();
  }
    
}