Release History
###############


v0.14.1 (2023-12-06)
====================

Bugfixes
--------
- Check existence of :any:`WeakPartialMethodSlot`'s ``signal_owner`` before
  attempting to disconnect a slot from its signal.

Contributors
------------
- tangkong


v0.14.0 (2023-10-16)
====================

Features
--------
- Adds :any:`WeakPartialMethodSlot`, which handles cleanup for partial methods
  used as qt slots (callbacks).
- Adds :any:`PydmDemotionFilter`, which makes Pydm-based applications with logging
  configurations less verbose at close when there are cleanup issues.

Contributors
------------
- tangkong
- zllentz


v0.13.0 (2023-09-27)
====================

Features
--------
- Add cleaned up and performant version of heavily-used :any:`get_info` in
  :mod:`pcdsutils.info`.

Maintenance
-----------
- Documentation building was fixed and pre-release note support was added.

Contributors
------------
- klauer


v0.12.2 (2023-04-20)
====================

This is a maintenance release, there are no functional changes to the
code in this release

What’s Changed
--------------

-  MAINT: bulk secrets and readme update by @ZLLentz in
   https://github.com/pcdshub/pcdsutils/pull/71


v0.12.1 (2023-02-23)
====================

This is a maintenance/ci-only release. There are no functional changes
to the library code.

What’s Changed
--------------

-  CI: move to GitHub actions by @klauer in
   https://github.com/pcdshub/pcdsutils/pull/69
-  DEV/MNT: migrate to latest standards with pyproject.toml [LCLSPC-603]
   by @klauer in https://github.com/pcdshub/pcdsutils/pull/70


v0.12.0 (2022-11-16)
====================

What’s Changed
--------------

-  MAINT: scripted fix for precommit by @ZLLentz in
   https://github.com/pcdshub/pcdsutils/pull/68
-  ENH: include slightly tweaked DesignerDisplay from atef by @ZLLentz
   in https://github.com/pcdshub/pcdsutils/pull/67


v0.11.0 (2022-07-14)
====================

What’s Changed
--------------

-  FIX: classmethods and staticmethods in profiler by @ZLLentz in
   https://github.com/pcdshub/pcdsutils/pull/59
-  ENH: import timing function using python built-in options by @ZLLentz
   in https://github.com/pcdshub/pcdsutils/pull/60
-  FIX: don’t log SyntaxError/NameError by @klauer in
   https://github.com/pcdshub/pcdsutils/pull/62
-  ENH: log exception filename/line number by @klauer in
   https://github.com/pcdshub/pcdsutils/pull/65


v0.10.0 (2022-06-02)
====================

What’s Changed
--------------

-  ENH: profile utils from typhos by @ZLLentz in
   https://github.com/pcdshub/pcdsutils/pull/47
-  ENH: Profiler follow up by @ZLLentz in
   https://github.com/pcdshub/pcdsutils/pull/53
-  ENH: add LazyWidget by @klauer in
   https://github.com/pcdshub/pcdsutils/pull/55


v0.9.0 (2022-04-29)
===================

What’s Changed
--------------

-  ENH: json-to-table by @klauer in
   https://github.com/pcdshub/pcdsutils/pull/49
-  STY/FIX: pre commit by @klauer in
   https://github.com/pcdshub/pcdsutils/pull/50


v0.8.0 (2022-03-11)
===================

What’s Changed
--------------

-  ENH: add ophyd helpers from typhos/atef by @klauer in
   https://github.com/pcdshub/pcdsutils/pull/46


v0.7.0 (2022-02-02)
===================

What’s Changed
--------------

-  ENH: get current experiment by @klauer in
   https://github.com/pcdshub/pcdsutils/pull/43
-  BUG: prospective fix for demotion filter ignoring handler log level
   by @ZLLentz in https://github.com/pcdshub/pcdsutils/pull/42
-  ENH: HelpfulIntEnum by @klauer in
   https://github.com/pcdshub/pcdsutils/pull/44

Summary
-------

-  Add utilities that originated in other pcds libraries
-  Fix a bug in the demotion filter


v0.6.0 (2021-11-08)
===================

What’s Changed
--------------

-  ENH: add tools for using python logging for warning handling by
   @ZLLentz in https://github.com/pcdshub/pcdsutils/pull/37
-  ENH: Add callback exception deduplication filter by @ZLLentz in
   https://github.com/pcdshub/pcdsutils/pull/39

Summary
-------

Added utilities for demoting the level of log messages and for
redirecting the warnings module to use the logging mechanisms. Most
relevant additions:

- :any:`pcdsutils.log.install_log_warning_handler`
- :any:`pcdsutils.log.DemotionFilter`
- :any:`pcdsutils.log.LogWarningLevelFilter`
- :any:`pcdsutils.log.OphydCallbackExceptionDemoter`


v0.5.0 (2021-07-22)
===================

Features
--------

-  Add central exception logging utilities that had previously been
   duplicated in both hutch-python and lucid.

Bugfixes
--------

-  Fix issues with the version difference display


v0.4.3 (2021-07-09)
===================

Set the default log protocol to TCP, rather than UDP, so it works on
hutch machines. Large UDP packets do not make it from hutch consoles to
the log hosts.


v0.4.2 (2021-03-23)
===================

-  Add missing username field to logger messages
-  Fix dependency issues


v0.4.1 (2021-01-19)
===================

Maintenance release, with CI and documentation updates.
No functional changes to the code.


v0.4.0 (2020-10-19)
===================

Features
--------

-  Add release notes utility that converts from Github releases to
   ``release_notes.rst`` for documentation.
-  Transplant bash script interfaces from ``pcdsdaq`` as a more central
   place to keep them. These currently include :any:`get_hutch_name`,
   :any:`get_run_number` and :any:`get_ami_proxy`


v0.3.1 (2020-09-17)
===================

-  Do not propagate central logger records to root. Central logger
   should only be shipping out to logstash, regardless of the root
   logging configuration.


v0.3.0 (2020-06-08)
===================

-  Improvements to ``requirements-compare``:

   -  Add ``--ignore-docs`` to which makes differences at the
      docs-requirements not a critical error
   -  Set exit code to 1 in case requirements are not matching


v0.2.0 (2020-05-15)
===================

-  Add requirements file-related utilities (comparison of
   ``requirements.txt`` and conda ``meta.yaml``)

   -  Adds console utilities ``requirements-from-conda``
   -  Adds console utility ``requirements-compare``

-  Relies on ``qtpynodeeditor`` for inheriting superclass properties


v0.1.1 (2020-03-13)
===================

Fixes win32 ``os.uname`` issue


v0.1.0 (2020-03-13)
===================

-  Interface to PCDS-wide logstash-based logging system
-  Qt tools
-  PopBar
-  Property forwarder


v0.0.0 (2020-01-24)
===================

Enjoy all of the features of *pcdsutils*:

- TODO
