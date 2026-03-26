ANTS: How to Contribute
=======================

Reporting Bugs
--------------

To report bugs/issues please email miao@metoffice.gov.uk and ideally open an
associated `bug report
<https://github.com/MetOffice/ANTS/issues/new?template=bug-report.md>`_
on GitHub as well.

To support the ANTS developers in identifying the problem, please provide:

* a recipe for repeating - what command/routine was called and with what
  arguments/inputs?
* any error message text output
* the version of ANTS being used
* the version of the ancillary-file-science code being used, if applicable
* if making a change to core or ancillary-file-science, branches checked into the repository.
  Please provide links and revision numbers.

Due to the complexity of some workflows it can be hard to understand what
is being run/intended, so when providing a recipe for repeating your issue
please try and provide details of the script(s) being run and the inputs and
arguments being used beyond just a pointer to "task X in workflow Y".

Feature Requests
----------------

We welcome input from our users on things that could make ANTS more useful,
easier to use, or add functionality that is missing for your desired ancillary
generation processes. If you would like to request an enhancement or behaviour
change please get in contact, describing the use case in detail and ideally open
an associated `feature request
<https://github.com/MetOffice/ANTS/issues/new?template=feature-request.md>`_
on GitHub as well.

Contribute Code
---------------

All contributions to ANTS are made via merges with the ``main``
branch of https://github.com/MetOffice/ANTS.

New contributors to ANTS must agree to the following Contributor Licence
Agreement (CLA), and add their name and institution to the list of contributors.

The CLA below supercedes the CLA that was previously used on the Met Office
Science Repository Service (MOSRS). Contributors who have previously contributed
code to ANTS via MOSRS must agree to the new CLA by adding their name and
institution to the list of contributors.

ANTS uses `pre-commit <https://pre-commit.com>`_ hooks.
If you are a first-time contributor, you may need to run the following command
once to install ``pre-commit`` into your local git repository::

    pre-commit install

You may need to activate an environment containing ``pre-commit`` before running.

Contributor Licence Agreement (v1.1)
------------------------------------

Thank you for your interest in contributing to ANTS, which is
managed by the Met Office.

In order to clarify the intellectual property license granted with
Contributions from any person or entity, ANTS must have a
Contributor License Agreement ("CLA") on file that has been signed by each
Contributor, indicating agreement to the license terms below. Each contributing
individual within a contributing organisation must personally sign the CLA form.

This license is for your protection as a Contributor as well as the protection
of ANTS and its users; it does not change your rights to use your own
Contributions for any other purpose.

To sign the CLA please add your name and institute in the `Code contributors`_
section at the bottom of this page. Signing of
this document constitutes a legally binding agreement between You and the Met
Office.

The Met Office will collect, use and process your Personal Data for the
purposes of supporting the development of ANTS and recording
ownership of contributions. Your Personal Data will be processed in accordance
with the Met Office Privacy Policy and UK and European Data Protection Laws
(the Data Protection Act 2018 and the General Data Protection Regulation EU
2016/680). The legal basis for processing is contractual necessity, as set out
in the Privacy Policy. Personal Data processed by the Met Office will not be
disclosed to third parties for marketing purposes. Your GitHub username will be
stored in order to permit Developers ANTS to ascertain that your
contribution is covered by a signed CLA. Your Personal Data will be stored in a
GitHub repository belonging to the ANTS administrators. For further information,
please see the `Privacy Policy
<https://www.metoffice.gov.uk/about-us/legal/privacy>`_.

To end this agreement please contact miao@metoffice.gov.uk. This will result in
your GitHub username being removed from the list of CLA signees and will prevent
further contributions being accepted to ANTS. Please be aware that for
purposes of recording previous agreements of Your existing Contributions, it is
not possible to withdraw the signed CLA from the historical archive. This does
not affect your rights as a data subject, as set out in the `Privacy Policy
<https://www.metoffice.gov.uk/about-us/legal/privacy>`_.

You accept and agree to the following terms and conditions for Your past,
present and future Contributions submitted to ANTS. In return, the Met
Office shall not use Your Contributions in a way that is contrary to the
interests of users of ANTS. Except for the license granted herein
to the Met Office and recipients of software distributed by ANTS, You
reserve all right, title, and interest in and to Your Contributions.

1. Definitions

"You" (or "Your") shall mean the copyright owner or legal entity authorized
by the copyright owner that is making this Agreement with the Met Office. For
legal entities, the entity making a Contribution and all other entities that
control, are controlled by, or are under common control with that entity are
considered to be a single Contributor.

For the purposes of this definition, "control" means (i) the power, direct
or indirect, to cause the direction or management of such entity, whether by
contract or otherwise, or (ii) ownership of fifty percent (50%) or more of the
outstanding shares, or (iii) beneficial ownership of such entity.

"Contribution" shall mean any original work of authorship, including any
modifications or additions to an existing work, that is intentionally submitted
by You to ANTS. For the purposes of this definition, "submitted"
means any form of electronic, verbal, or written communication sent to ANTS
or the Met Office or their representatives or members, including but
not limited to communication on electronic mailing lists, source code control
systems, and issue tracking systems that are managed by, or on behalf of, ANTS
for the purpose of discussing and improving the Work, but excluding
communication that is conspicuously marked or otherwise designated in writing
by You as "Not a Contribution".

"Met Office" shall mean the Met Office, an Executive Agency of the
Department for Science, Innovation and Technology of the United Kingdom of
Great Britain and Northern Ireland ("DSIT"), whose principal place of business
is situated at FitzRoy Road, Exeter, Devon EX1 3PB, United Kingdom, for and on
behalf of DSIT.

"ANTS" shall mean tools made available under the ANTS name and/or
logo, and published through public channels such as
https://github.com/MetOffice/ANTS.

"Parties" shall mean the Met Office and You.

"Working Day" shall mean a day other than a Saturday, Sunday or public
holiday in England when banks in London are open for business.

"Personal Data" shall have the meaning given in s.3 of the Data Protection
Act 2018.

2. Grant of copyright license

Subject to the terms and conditions of this Agreement, You hereby grant to
the Met Office and to recipients of ANTS a perpetual, worldwide,
non-exclusive, royalty-free, irrevocable copyright license to reproduce,
prepare derivative works of, publicly display, publicly perform, sublicense,
and distribute Your Contributions and such derivative works under the terms of
the license specified for ANTS to which a Contribution is
submitted. Details of the license specified for ANTS shall be
located in the LICENSE file of the source code repository. The
license chosen for ANTS shall be one of the open source licenses
from the list maintained by the Open Source Initiative (OSI)
(https://opensource.org/licenses).

You agree and acknowledge that the Met Office may sublicense and distribute
your Contributions under any subsequent version of the licence specified for
ANTS to which your Contribution was made. Furthermore, You agree
that, by agreement through the standard ANTS governance process, ANTS
may change the license from time to time to an alternative open source
license from the list maintained by the OSI in order to suit the evolution of
ANTS.

3. Intellectual property infringement

If any third party makes any claim against You or any other entity, alleging
that your Contribution, or the work to which you have contributed, infringes
the intellectual property rights of that third party, then You shall inform the
Met Office within five (5) Working Days of such claim in order for the Met
Office to take all appropriate action it deems necessary in relation to the
claim.

4. Legal entitlement

You represent that you are legally entitled to grant the above license. If
your employer(s) has rights to intellectual property that you create that
includes your Contributions, you represent that you have received permission to
make Contributions on behalf of that employer, or that your employer has waived
such rights for your Contributions to ANTS.

5. Contribution of Your creation(s)

You represent that each of Your Contributions is Your original creation and
that you have not assigned or otherwise given up your interest in the
Contribution to any third party. You represent that Your Contribution
submissions include complete details of any third-party licence or other
restriction (including, but not limited to, related patents and trademarks) of
which you are personally aware and which are associated with any part of Your
Contributions.

6. Notification

You agree to notify the Met Office of any facts or circumstances of which
you become aware that would make these representations inaccurate in any
respect. You further agree to fully indemnify, and keep indemnified, the Met
Office against any losses suffered as a result of any fraudulent or negligent
misrepresentation made by you under Clauses 4 or 5.

7. Dispute resolution

The Parties shall attempt in good faith to negotiate a settlement to any
dispute arising between them out of or in connection with this Agreement within
30 Working Days of the dispute arising.

If the dispute cannot be resolved, then the Parties shall attempt to settle
it by mediation in accordance with the Centre for Effective Dispute Resolution
("CEDR") Model Mediation Procedure from time-to-time in force.

To initiate the mediation a party to the Agreement must give notice in
writing (the "ADR Notice") to the other party requesting mediation in
accordance with this clause.

8. Mediation

The mediation is to take place not later than 30 Working Days after the ADR
Notice. If there is any issue on the conduct of the mediation upon which the
Parties cannot agree within 14 Working Days of the ADR Notice, then CEDR shall,
at the request of either party, decide the issue for the Parties, having
consulted with them.

Unless otherwise agreed, all negotiations connected with the dispute and any
settlement shall be conducted in confidence and without prejudice to the rights
of the Parties in any future proceedings.

If the Parties reach agreement on the resolution of the dispute, the
agreement shall be reduced to writing and shall be binding on the Parties once
it is signed by both You and the Met Office.  If the Parties fail to reach
agreement within 60 Working Days of the initiation of the mediation, or such
longer period as may be agreed by the Parties, then any dispute or difference
between them may be referred to the courts.

Nothing in this Agreement affects the right of You or the Met Office to
apply to the court for urgent interim equitable relief (including, but not
limited to, an injunction).

9. General

For the purposes of clarity: this Agreement constitutes a contract for the
grant of a license and not a contract of employment.

No waiver by either party of any of its rights under this Agreement shall
release the other party from full performance of its other obligations stated
herein.

Nothing in this Agreement shall be deemed to constitute, evidence, or
comprise a partnership between the Parties or to constitute either party the
agent of the other.

Neither party may assign its rights under this Agreement in whole or in part
to any person, firm or company without the prior written agreement of the other
party.

No amendment, waiver, or variation, of this Agreement, whether in whole or
in part, shall be binding on the Parties unless set out in writing and signed
by or on behalf of the Parties by their duly authorized representatives.

If any provision of this Agreement is held by a competent authority to be
illegal, invalid, or unenforceable, whether in whole or in part, the validity
of the remainder of the relevant provision and the remaining provisions shall
not be affected or prejudiced.

Each party shall, at its own cost and expense, from time to time do or
procure the execution of all documents as may be reasonably necessary in order
to give effect to the provisions of this Agreement.

The Parties to this Agreement do not intend that any of its terms will be
enforceable by any person not a party to it.

This Agreement shall be governed by and construed in accordance with the
laws of the England and Wales.

Code contributors
-----------------

The following people have contributed to this code under the terms of the
Contributor Licence Agreement:

* Josh Rackham (Met Office)
* Harold Dyson (Met Office)
* Theo Geddes (Met Office)
* Andrew Clark (Met Office)
* Jennifer Hickson (Met Office)
