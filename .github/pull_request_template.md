Closes #<issue number>

To be completed prior to review request **and updated** as required during the review process.

If the answer to an item on the list is not applicable, feel free to replace the checkbox with 'N/A' to give extra clarity.

**All developers are reminded to follow the [ancil working practices](https://code.metoffice.gov.uk/trac/ancil/wiki/ANTS/WorkingPractices)**

-----

### Branch

**Related branches (e.g. contrib):**<br>
[please link any related branches here]

**ANTS rose stem logs** <br>
[please enter the workflow name here as it has been run e.g. ants-trunk/run5] <br>


**contrib rose stem logs** <br>
[please enter the workflow name here as it has been run e.g. ants-contrib/run1] <br>

-----

### Testing

For core ANTS only tests, the bare minimum that will be accepted is the `--group=unittests` but many, if not most, changes will need to test other groups to ensure they meet reviewer expectations. In general, it should be possible and is advised to run the `--group=all` group prior to review submission as this will catch any consequential issues. **Additionally** you **must** run the contrib tests, pointing at your branch, with `--group=all` to capture any behaviour changes affecting Science codes.

If your change will alter existing science results, you will need to seek appropriate Scientific validation and confirm that the model has been initialised with your new development. Inspecting a change in xconv/pyplot/visualiser of choice is not sufficient to demonstrate the model can be initialised from your file.

------

**Impact of change**

- [ ] This will maintain results for ANTS `rose stem --group=all` tests
- [ ] This will this maintain results for contrib `rose stem --group=all` tests
- [ ] If this change adds a new capability, evidence has been supplied to show testing of ancillary generation across different resolutions e.g. For global ancillary generation capabilities for use in NWP n1280e is expected to have been tested
- [ ] This change has significantly impacted required resources (runtime and memory) in existing ancillary generation (if yes, give details)
- [ ] This change alters existing ancils

<div>
Add further comments/details for your reviewers here on the impacts of the change......
</div>

----

**Approvals for this change**

- [ ] I have approval from the ANTS core development team for these changes

------

**New functionality further testing**

- [ ] If adding new functionality to existing codes, I confirm that the new code doesn't change results when it is switched off and ''works'' when switched on
- [ ] Unittests have been added
- [ ] Rose stem tests have been added for any new functionality
- [ ] If adding new functionality please confirm that the new code compares across different standard decompositions.
- [ ] I have not encountered any failures in my rose-stem output(s) <br>These tasks **must** succeed for your ticket to pass review.
- [ ] I have remembered to run the code style check tasks/tools


<div>
Add details of any further testing here.
</div>

------

**Other**
- [ ] I read the [Contributor Licence Agreement](https://metoffice.github.io/ANTS/contributing.html#contributor-licence-agreement-v1-1)
- [ ] I have added my name and affiliation to the [Contributors list](https://github.com/MetOffice/ANTS/blob/main/CONTRIBUTING.rst#code-contributors) if I am not already on there.
- [ ] The ticket labels, milestones, etc. are correct
- [ ] Links to all related tickets have been provided in the ticket description
- [ ]  I have requested a code reviewer
- [ ] Source data has been added or changed - please include a link to the license (so we can check that it will allow us to store derived works as sources and KGOs in the repository)

| | |
|---|---|
| I confirm that all code is my own and that my contributions are not subject to copyright or license restrictions (see [Contributor Licence Agreement](https://metoffice.github.io/ANTS/contributing.html#contributor-licence-agreement-v1-1)). | **your name** |
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
