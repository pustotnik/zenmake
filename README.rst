# ZenMake

[![Licence](https://img.shields.io/pypi/l/zenmake.svg)](https://pypi.org/project/zenmake/)
[![Python](https://img.shields.io/pypi/pyversions/zenmake.svg)](https://pypi.org/project/zenmake/)
[![PythonImpl](https://img.shields.io/pypi/implementation/zenmake.svg)](https://pypi.org/project/zenmake/)
[![PyPI](https://img.shields.io/pypi/v/zenmake.svg)](https://pypi.org/project/zenmake/)
[![Travis](https://travis-ci.com/pustotnik/zenmake.svg?branch=master)](https://travis-ci.com/pustotnik/zenmake)
[![coveralls](https://coveralls.io/repos/github/pustotnik/zenmake/badge.svg)](https://coveralls.io/github/pustotnik/zenmake)
[![ProjectStatus](https://img.shields.io/pypi/status/zenmake.svg)](https://pypi.org/project/zenmake/)

## Brief
ZenMake - build system based on WAF (https://waf.io/). It's designed to be as simple as possible to use but be flexible.
It is not self-sufficient build system. It's superstructure above WAF. You can regard it as some kind of extension for WAF. I don't try to hide that WAF does most the part. It's for C/C++ projects now but may be later I will add some other languages. Especially WAF supports a lot of other languages. It is not universal build system and is not applicable for any C/C++ project. But I hope it will be useful. I began this project for building my own C++ projects. Anyone can use this as example of using WAF also. It supports building on GNU/Linux, MS Windows and Apple MacOS. It should work on some other platforms (FreeBSD for example) but it's not tested.

## Why?
https://news.ycombinator.com/item?id=18789162
> Cool. One more "new" build system...

Yes, I know, we have already a lot of them.
I decided to create this project because I hadn't found build tool for linux which is easy to use, flexible, ready to use, with declarative configuration and suitable for me. I know about lots of build systems. I have read about all modern and popular such systems. And I have tried some of them. As result I have concluded that I had to try to make my own build tool. I have already experience in creation of custom build tool based on WAF on my work in the past. So why not? I do it mostly for myself. But I will be glad if my tool be useful for someone else.

Main purpose of this project is to make build tool for most of the simple cases. I mean it is for cases where no need to make very complex configuration for building. But where it's possible this tool will save flexibility. It's not the fastest build system but it has enough good performance. I want a simple, stable build tool that just works.

Below I describe what is wrong with some of existing build systems in my opinion. I regarded only build systems that can build C/C++ projects.

#### CMake
It's one of the most popular cross platform build systems nowadays. But I don't know why this system is so popular. I have never liked its internal language. For me it's terrible. As I know a lot of people also think so but selects it because it's popular thing with good supporting for many platforms. But anyway CMake is too complicated and not easy to use.

One more fact: a lot of people decided to select/migrate to meson after meson has been created. And it says that meson is better for them.

#### Make
It's very old but actual build system. But because it has too many disadvantages other more young build systems were created. Anyway it is used as backend for some other build systems, for example in CMake.

#### WAF
WAF is a great build system. It has a lot of possibilities. I like it and have some experience with it. But for me it's meta build system. You can build your projects only with WAF and nothing else. But before you should learn a lot about this system. So it is not easy to use.

#### ninja
Well. I don't know a lot about this system. I know that it is used as backend in Meson and CMake. And as I understand that this systems definitely is not easy to use and it requires a lot of actions to use.

#### Meson
It's really not bad build system which uses ninja as a backend to build. I tried to use it. And as result I don't like some features of it:

- It tries to be smart when it's not necessary.
- They offer to use internal language which is like python but it is not python. You can read more details about it here: https://mesonbuild.com/FAQ.html#why-is-meson-not-just-a-python-module-so-i-could-code-my-build-setup-in-python. But such reasons do not use 'real' language are not critical for me. I don't say that all reasons are silly or something like that. I just know that it is not possible to make the best system all the world. Each of them has own advantages and disadvantages. At least 'real' language gives you more freedom to make things.
- It doesn't support target files with a wildcard: https://mesonbuild.com/FAQ.html#why-cant-i-specify-target-files-with-a-wildcard
- They claim that meson is 'as user friendly as possible' but I think it can be more user friendly in some things.

Position 'wildcard for target files is bad thing' exists also in CMake. I don't agree with the position of developers of Meson and CMake that specifying target files with a wildcard is a bad thing. For example authors of Meson wrote that it is not fast. Yes, I agree that for big projects with a lot of files it can be slow in some cases. But for all others it can be fast enough. Why didn't they make it as option? I don't know. Variant with external command in meson doesn't work very well and authors of Meson know about it. In WAF I don't have any problems with it.

#### Scons
Nowadays we have WAF already. Scons is already too old and slow.

#### Premake/GENie
Actually I did't try to use it and I've forgotten about that. But it's not build system. It's generator for some other build systems and IDE. This is another way to build projects. I don't know how it is useful but it has status beta/alfa. I have checked some modules and it looks like something is working but something is not. And it looks like something too complex inside. Description of project looks good. Perhaps I had to try to use it.

Hm, here I found some info about problems with premake: https://medium.com/@julienjorge/an-overview-of-build-systems-mostly-for-c-projects-ac9931494444. And I don't like it.


## Usage
TODO: I will add info when tool will be really ready to use.
