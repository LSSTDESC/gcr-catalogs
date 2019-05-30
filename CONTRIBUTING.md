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


5. Make changes

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

