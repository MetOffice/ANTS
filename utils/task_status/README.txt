# Ants formatted test log generator

##Description: 
This is a tool for generating a file named "test_results_logs.txt" of the 
successes/failures from an ANTs test run on a workflow. The user has the choice 
of two types of formatting; Trac or GitHub.

##Requirements: 
- python 3.10.13
- A "db"(database) file resulting from a cylc run (this should be found in
~/cylc-run/<suite-id>/runN/log/db).

##How to use:
The tool requires three arguments:
1. The full path to the cylc-run database file.
2. The full path and desired filename where you want the formatted logs generated.
3. The style of formatting for the output file ("trac" for Trac, "gh" for Github).

An example of it's usage would be as follows:

$ python3 generate_ants_test_logs.py <path/to/origin/database/file/>
<path/to/output/folder/> <choice of formatting("trac"/"gh").