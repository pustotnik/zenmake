# raven

## Brief
This is one more building system based on WAF (https://waf.io/). It's for C/C++ projects mostly but may be later I will add some other languages. Especially WAF supports a lot of other languages. It is not universal build system and is not applicable for any C/C++ project. But I hope it will be useful. I began this project for building my own C++ projects.

## Why?
I decided to create this project because I hadn't found build system for linux which is easy to use, flexible, ready to use and with declarative configuration. I know about lots of build systems. I have read about all modern and popular such systems. And I have tried some of them. As result I concluded that I had to try to make my own build system. I have already experience in creation custom build systems based on WAF on my work in the past.

Main purpose of this project is to make build system for most of simple cases. I mean it is for cases where no need to make very complex configuration for building. But where it's possible this system will have flexibility.

Below I describe what is wrong with some of existing build systems in my opinion. I regarded only build systems that can build C/C++ projects.

#### CMake
It's one of the most popular cross platform build systems nowadays. But I don't know why this system is so popular. I have never liked its internal language. For me it's terrible. As I know a lot of people also think so but select it because it's popular thing with good supporting. One more fact: a lot of people decided to select/migrate to meson after meson has been created. And it says that meson is better for them.

#### Make
It's very old but actual build system. But because it has too many disadvantages other more young build systems were created. Anyway it is used as backend for some other build systems, for example in CMake.

#### WAF
WAF is a great build system. It has a lot of possibilities. I like it and have some experience with it. But for me it's meta build system. You can build your projects only with WAF and nothing else. But before you should learn a lot about this system. So it is not easy to use.

#### ninja
Well. I don't know a lot about this system. I know that it used as backend in meson and CMake. And as I understand this systems definitely is not easy to use and it requires a lot of actions to use. 

#### meson
It's really not bad build system which uses ninja as a backend to build. But I don't like some features of it:

- It tries to be smart when it's not necessary.
- They offer to use internal language which is like python but it is not python. You can read more details about it here: https://mesonbuild.com/FAQ.html#why-is-meson-not-just-a-python-module-so-i-could-code-my-build-setup-in-python. But such reasons do not use 'real' language are not critical for me. I don't say that all reasons are silly of something like that. I just know that it is not possible to make the best system all the world. Each of them has own advantages and disadvantages. At least 'real' language gives you more freedom to make things.
- It doesn't support target files with a wildcard: https://mesonbuild.com/FAQ.html#why-cant-i-specify-target-files-with-a-wildcard

Last feature exists also in CMake. I don't agree with the position of developers of Meson and CMake that specifying target files with a wildcard is a bad thing. For example authors of Meson wrote that it is not fast. Yes, I agree that for big projects with a lot of files it can be slow in some cases. But for all others it can be fast enough. Why didn't they make it as option? I don't know. Variant with external command in meson doesn't work very well and authors of Meson know about it. In WAF I don't have any problems with it.

#### Scons
Nowadays we have WAF already. Scons is already too old and slow.

## Why is it called raven?
Why not? It's just name. Like ninja or meson.

## Usage
TODO
