# copytags utility

## Add a python CLI utility to copy tags from one photo database to another.

- Implement in python.
- Follow project coding style and conventions.
- Use the click library to create a CLI utility.
- The utility should take two arguments, the source database and the destination database.
- The utility should copy all tags from the source database to the destination database for photos that have the same md5sum.
- Write a permanent unittest to test the copytags feature.
- Verify that the copytags features works by running and resolving the unittest failures.
- As tasks are completed, update the PLAN.md file with the completed tasks in the copytags section of PLANS.md.
- Modify copytags.py toIterate over the smallest database. Match photo records based on md5sum. Copy tags from the source database to the destination database. Use the tqdm library to show a progress bar.



