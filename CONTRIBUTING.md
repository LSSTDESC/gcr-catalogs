# Contribute to GCRCatalogs:

1. On GitHub [fork](https://guides.github.com/activities/forking/) the GCRCatalogs GitHub repo.

2. On NERSC, clone your fork (you can skip this if you've done it)

       cd /your/own/directory
       git clone git@github.com:YourGitHubUsername/gcr-catalogs.git
       cd gcr-catalogs
       git remote add upstream https://github.com/LSSTDESC/gcr-catalogs.git


3. Sync with the upstream master branch (**always do this!**)

       cd /your/own/directory/gcr-catalogs
       git checkout master
       git pull upstream master
       git push origin master


4. Create a new branch for this edit:

       git checkout -b newBranchName master


5. Develop a new reader or make changes to an exisiting reader

       If you are writing a new reader please see https://github.com/yymao/generic-catalog-reader#usage
       for an overview and a simple example of a minimal reader. The guide will explain that your 
       reader must be a subclass of a generic GCRCatalogs parent class and that you will need to 
       supply a minimum of 3 methods and atranslation dictionary between the quantities in your 
       catalog and the quantities that are presented to the user via the GCRCatalogs interface. 
       You can also peruse the code for the various readers in this repository for additional
       examples. 
       You will also need to supply a yaml configuration file that lives in the catalog_configs 
       subdirectory for GCRCatalogs. This configuration file specifies the location of your catalog
       and any other important input parameters. 
       
       Otherwise, make your changes as desired.
       
6. Test by adding your clone to the path when running Python: 
   ```python
   import sys
   sys.path.insert(0, '/your/own/directory/gcr-catalogs')
   ```   
   You can also use `pytest` to run a minimal set of tests. 

7. Commit and push to your forked repo

       git add <files changed>
       git commit -m <short but meaningful message>
       git push origin newBranchName

8. Go to your forked repo's GitHub page and "create a pull request". 

