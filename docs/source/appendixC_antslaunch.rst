.. meta::
   :description lang=en: Information about the ants-launch script
   :keywords: appendix, run, application, module
   :property=og:locale: en_GB    

.. _ants_launch:

========================================
Appendix C: ants launch
========================================

ants-launch is a  convenience script intended for use at sites where ants, scitools
and um_tools are available via module load commands. Where such central
provisioning is available the expected usage for most users is to want to
use the **ANTS_MODULE** to load in an ants module. The **SCITOOLS_MODULE** and
**UM_UTILS_MODULE** options are provided for those wishing to deploy their own
ANTS builds. A **PYTHONPATH_PREPEND** variable is used to extend the pythonpath
after loading in the appropriate module(s). Similarly, a **PATH_PREPEND**
variable is available for adding items to the path after loading in modules.

USAGE
    ants-launch CMD_WITHOPTS

ENVIRONMENT
    ANTS_MODULE
        The version of ants you want to run. If set, this will take precedence over loading scitools and um_tools.
    SCITOOLS_MODULE
        The version of the software stack you want to run. Will not be used if ANTS_MODULE is set.
    UM_UTILS_MODULE
        The version of the UM_UTILS module you want to run (if any). Use this to load mule on top of a scitool module. N.B. Will only be loaded if a scitools module has been loaded.
    PYTHONPATH_PREPEND
        Path to a library you want to prepend to PYTHONPATH.
    PATH_PREPEND
        Path you want to prepend to PATH.
    ULIMIT_SETTING
        Specify a value you want to be passed to ulimit -s. Typically set to unlimited for tasks using spiral search.
    QUIET_MODE
        Use this when you don't want confirmation messages being printed to stdout, for example when running an eval script

OPTIONS
    CMD_WITHOPTS
        The command you want to invoke with options
