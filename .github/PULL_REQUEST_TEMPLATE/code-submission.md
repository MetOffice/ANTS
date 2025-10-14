# Ticket Summary <#Enter_ticket_number_here>
## Author: <Enter_your_name_here>

To be completed prior to review request **and updated** as required during the review process.

**All developers are reminded to follow the [ancil working practices](https://code.metoffice.gov.uk/trac/ancil/wiki/ANTS/WorkingPractices)**

-----

### Branch

**Code branch(es)** <br>
Related branches (e.g. contrib):


**ANTS rose stem logs** <br>
[please enter the workflow name here as it has been run e.g. ants-trunk/run5] <br>


**contrib rose stem logs** <br>
[please enter the workflow name here as it has been run e.g. ants-contrib/run1] <br>

-----

### Testing

For core ANTS only tests, the bare minimum that will be accepted is the `--group=unittests` but many, if not most, changes will need to test other groups to ensure they meet reviewer expectations. In general, it should be possible and is advised to run the `--group=all` group prior to review submission as this will catch any consequential issues. **Additionally** you **must** run the contrib tests, pointing at your branch, with `--group=all` to capture any behaviour changes affecting Science codes.

For contrib tests, the bare minimum that will be accepted is the `--group=unittests,qa` but many, if not most, changes will need to test other groups to ensure they meet reviewer expectations.
For example, `--group=orography`, `--group=soil`, `--group=lai` etc. when working on code in those groups. <br> To run every test use `--group=all`.

If your change will alter model evolution, affect other linked ancillary generation processes, or provides a new ancillary capability, you will need to seek appropriate Scientific validation and confirm that the model has been initialised with your new development. Inspecting a change in xconv/pyplot/visualiser of choice is not sufficient to demonstrate the model can be initialised from your file.

------

|**Impact of change**| |
|--- | --- |
| Will this maintain results for ANTS `rose stem --group=all` tests? | **YES/NO** |
| Will this maintain results for contrib `rose stem --group=all` tests? | **YES/NO** |
| If this change adds a new capability, has evidence been supplied to show testing across different ANTS decomposition options (typically 0,1,2 in rose stem)? 'where applicable'' | **YES/NO/NA** |
| If this change adds a new capability, has evidence been supplied to show testing of ancillary generation across different resolutions? e.g. For global ancillary generation capabilities for use in NWP n1280e is expected to have been tested | **YES/NO/NA** |
| Has your change significantly impacted required resources (runtime and memory) in existing ancillary generation? | **DETAILS/NO** |
| Does your change alter existing ancils? | **YES/NO** |

<div>
Add further comments/details for your reviewers here on the impacts of the change......
</div>

----

|**Approvals for this change**| |
| --- | --- |
| Have you got approval from the ANTS core development team for changes to codes in core ANTS? | YES/NO |
| Have you got approval from the relevant [Ancillary Science Owner(s)](https://code.metoffice.gov.uk/trac/ancil/wiki/ANTS/SteeringGroup/DraftScienceOwners) for this change? | YES/NO/NA |
| Have you got approval from the relevant [Ancillary Workflow Owner(s)](https://code.metoffice.gov.uk/trac/ancil/wiki/ANTS/SteeringGroup/DraftScienceOwners) for this change? | YES/NO/NA |
| If this is a new ancillary capability, who will become the [Ancil Science Owner](https://code.metoffice.gov.uk/trac/ancil/wiki/ANTS/SteeringGroup/TermsOfReference#AncilScienceowners) for this change? | **NAME** |

------

|**New functionality further testing**| |
| --- | --- |
| If adding new functionality to existing codes, please confirm that the new code doesn't change results when it is switched off and ''works'' when switched on? | **YES/NO/NA** |
| Has the new functionality had unittests added? | **YES/NO/NA** |
| Has the new functionality been added to and tested in Rose Stem? | **YES/NO/NA** |
| If adding new functionality please confirm that the new code compares across different standard decompositions. | **YES/NO/NA** |
| Have you encountered any failures in your rose-stem output(s)? <br>These tasks **must** succeed for your ticket to pass review. | **YES/NO** |
| Have you remembered to run the <code style check tasks/tools> | **YES/NO/NA** |


<div>
Add details of any further testing here.
</div>

------

|**Other**| |
| --- | --- |
| For non-Met Office staff, have you signed and returned the [Contributor Licence Agreement](https://code.metoffice.gov.uk/doc/ancil/ants/latest/appendixB_CLA.html)? | **YES/NO/NA** |
| Are the ticket components, keywords, etc. correct? | **YES/NO** |
| Have links to all linked tickets been provided in the ticket description? | **YES/NO/NA** |
| Have you <requested a code reviewer>? | **YES/NO** |
| Has source data for rose stem been added or changed?  If so, does the licence for the source data allow us to store derived works as sources and KGOs in the repository?  Please include a link to the licence.  | **YES/NO** |
| I confirm that all code is my own and that my contributions are not subject to copyright or license restrictions (see [Contributor Licence Agreement](https://code.metoffice.gov.uk/doc/ancil/ants/latest/appendixB_CLA.html)). | **your name** |
| I confirm I have not knowingly violated intellectual property rights (IPR) and have taken [sensible measures to prevent doing so](https://code.metoffice.gov.uk/trac/ancil/wiki/ANTS/WorkingPractices#LicencecopyrightandIPR), including appropriate [attribution for usage of Generative AI](https://code.metoffice.gov.uk/trac/ancil/wiki/ANTS/WorkingPractices#AIassistanceandattribution). I confirm that this work is my own, and I understand that it is my responsibility to ensure I am not violating others’ IPR.  This includes taking reasonable steps to ensure that all tools used while creating this contribution did not infringe IPR. | **your name** |

<div>
Please add any further notes here.  If Generative AI tools have been used, a brief summary (e.g. "Github copilot used to add extra unittests") should be provided.
</div>

--------
### Rose stem logs

Please copy in the contents of your trac_status.log file(s) below (found in the cylc-run directory for your rose stem run) to your rose-stem testing here. **Note**: if your changes lead to a change in answers, you must run `rose stem --group=all` to help ensure all affected configurations has been flagged up.

<div>
Add trac_status.log contents for ANTS rose-stem here.
</div>
<br>
<div>
Add trac_status.log contents for contrib rose-stem here.
</div>
