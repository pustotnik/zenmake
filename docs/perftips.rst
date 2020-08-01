.. include:: global.rst.inc
.. highlight:: console
.. _perftips:

Performance tips
================

Here are some tips which can help to improve performance of ZenMake in some cases.

Hash algorithm
"""""""""""""""""""""
By default ZenMake uses sha1 algorithm to control changes of config/built files
and for some other things. Modern CPUs often has support
for this algorithm and sha1 shows better or almost the same
performance as md5 in this cases. But in some other cases md5 can be
faster and you can switch to use this hash algorithm. However, don't expect big
difference in performance of ZenMake.

It's recommended to check if it really has positive effect before using of md5.
To change hash algorithm you can use parameter ``hash-algo`` in buildconf
:ref:`features<buildconf-features>`.

Task features
"""""""""""""""""""""
Prefer using ``<lang>stlib``/``<lang>shlib``/``<lang>program`` instead of aliases
``stlib``/``shlib``/``program`` in :ref:`features<buildconf-taskparams-features>`.
Using these aliases is always slower than without ones and for some projects
with a lot of files it can be significant.
