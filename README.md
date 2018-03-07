# Testing salt states with kitchen
`kitchen` provides a test harness to execute infrastructure code on one or more platforms in isolation.
The modular setup of kitchen allows for different cloud providers to execute the same test setup.
For example you could run kitchen for local development using Vagrant + VirtualBox while also having a
continuous integration process in place that spins up an EC2 instance to run tests on.

`kitchen` is a tool that was initially developed to be used for testing [Chef](https://chef.io) recipes.
But due to community development it expanded into something more powerful than that. 
An entire [ecosystem](https://github.com/test-kitchen/test-kitchen/blob/master/ECOSYSTEM.md) with lots of plugins
and support for different configuration management/provisioning tools is now available for use.

In our case we're using SaltStack for our configuration management and have a plethora of states that could rebuild
our infrastructure in case of failure and allows us to update multiple servers at once with some simple invocations. 
This idea behind this is known as 'infrastructure as code'. But, humans being humans, mistakes are made and as we all know 
things can and will go wrong while writing code. However the last thing you'd want to happen is for a server to fail,
unable to be recovered and have the Salt states unable to run because of a regression error you didn't catch during 
your time developing the states. You want to catch these errors early on in your development process. And you want to 
keep verifying that new changes being introduced do not alter the expected behaviour.

This is the reason why it should be possible to test your Salt states. Not just for syntax while developing 
(will this state render as expected when applied?) but also for expected behaviour. (is the service I set up really running 
and listening on the specified port?)

Enough talk, let's see how we can do this within our own development process using `kitchen`.

---

## Table of contents
- [Testing salt states with kitchen](#testing-salt-states-with-kitchen)
    - [Table of contents](#table-of-contents)
    - [Prerequisites](#prerequisites)
        - [Ruby](#ruby)
        - [Python](#python)
        - [Vagrant + VirtualBox](#vagrant-virtualbox)
        - [Gems and Pip packages](#gems-and-pip-packages)
        - [kitchen usage](#kitchen-usage)
    - [Writing your own tests using Python](#writing-your-own-tests-using-python)
    - [Contributing](#contributing)
    - [Contributors](#contributors)
    - [Changelog](#changelog)
    - [Get in touch with a developer](#get-in-touch-with-a-developer)
    - [License](#license)

## Prerequisites
Before you can get started you'll need a few things setup on your system.

### Ruby 
Version 2.4 is preferred but this will work with versions >= 1.9. 
I prefer using [rvm](https://rvm.io) to manage my different Ruby setups but this is not required.
[Here's](https://rvm.io/rvm/install) some information on getting rvm set up.

### Python
Both Python 2 and 3 will work fine. Again, you could use [virtualenv](https://virtualenv.pypa.io) to manage your Python
setup but this is not required. Also make sure that `pip` is installed alongside your Python installation.

### Vagrant + VirtualBox
Both [Vagrant](https://www.vagrantup.com) and [VirtualBox](https://www.virtualbox.org) need to be installed in order to continue.

### Gems and Pip packages
Once you have the prerequisites setup on your system it's now time to get setup. Open a terminal and `cd` into the saltstack repository.
```
$ cd ~/dev/saltstack # or wherever you've got the repo checked out
```
First we'll install `bundler`, a package manager for Ruby, and use that to install the Gems that are specified in the `Gemfile`.
```
$ gem install bundler
$ bundle install
```
Once the Ruby Gems are installed we'll need to setup the Python packages using `pip` which can be found in the `requirements.txt` file.
```
$ pip install -r requirements.txt
```
That's it! You're now ready to write and run kitchen tests.

### kitchen usage
Now that everything's set up it's time to learn how to use `kitchen` and write tests that can be run locally.

`kitchen` has one point of entry, the `.kitchen.yml` file living in the root of our project. Here's an example setup of the `.kitchen.yml` file:

```yaml
---
# The driver part of this file tells kitchen what platform to 
# provision and run tests on. This can be swapped for other drivers
# such as EC2/DigitalOcean etc.
driver:
  name: vagrant

# The platforms part tells the driver on what system we want to test our salt states.
# It is possible to run tests on multiple OS versions and see if there 
# is any difference.
platforms:
  - name: debian/contrib-jessie64 # use a debian 8 vagrant box

# The salt_solo provisioner tells kitchen to setup a salt-minion on the VM and run 
# a state.apply once the salt/pillar folders are synced to their respective places. 
provisioner:
  name: salt_solo
  is_file_root: true
  local_salt_root: '.'
  state_top_from_file: true
  require_chef: false
  salt_copy_filter:
    - .git
  # These grains will be set in each suite (global grains)
  grains:
    kitchen: enabled

# Suites make it possible to test with different setups. For example you could 
# set a custom grain per suite, and run py.test in the directory containing tests 
# for this particular setup. Each suite will create a seperate Vagrant box during 
# testing in order to execute tests in isolation of each other.
suites:
  - name: base
    # A verifier is used to check if the system that was just provisioned is
    # in the state that we expect it to be. It uses the Python tests that we
    # can write ourselves.
    verifier:
      name: shell
      command: py.test -v test/base

  - name: prometheus
    provisioner:
      grains:
        # Example of using a different grain to run different states per test suite.
        server_role:
          - prometheus
    verifier:
      name: shell
      command: py.test -v test/prometheus/
```

With this file in place it's as simple as running `kitchen test` to test our Salt states. `kitchen` will spin up a Vagrant box, provision
it with Salt and run our Python tests against the VM to see if everything's as our tests expect them to be. 

Here's a quick overview of some commands that can be useful while developing with `kitchen`:

* `kitchen create` - create the Vagrant box using the specified image in the `platforms` section of our YAML.
* `kitchen converge` - install `salt-minion` and run a `state.apply`. This can be very handy while writing states so that you can reapply a state you've just rewritten.
* `kitchen login` - drops you into shell of your Vagrant box. Allows you to debug as needed.
* `kitchen verify` - runs the test suite. When used like `kitchen converge && kitchen verify` this applies your new states and immediately runs the Python tests.
* `kitchen destroy` - as expected, it will destroy your Vagrant box.
* `kitchen test` - a combination of `create` and `converge` but also runs the `verifier`'s defined in the `suites`. (Python tests in our case)

***Note: If the kitchen command can't be found in your path try running it with `bundle exec` prepended (e.g. `bundle exec kitchen test`)***

## Writing your own tests using Python
It's all good and well that you can run the existing `kitchen` test suite but ofcourse you'd like to write your own tests so that you can verify that your new states are working as expected.
Lucky for you I was just going to get to that! (the title gave it away didn't it?)

Tests can be written in Python using `testinfra`, a library that is built on top of the popular `py.test` framework. It provides a simple DSL that can be leveraged to test infrastructure
states with. Documentation for `testinfra` can be found [here](https://testinfra.readthedocs.io).

Let's write some test to see if our Prometheus servers are setup as expected. We'll create a `test/prometheus` directory and place our tests in there.

***Note: All Python test functions should start with `test_` e.g. `test_nginx_installed`***

```python
# tests/prometheus/test_prometheus.py

def test_prometheus_is_running(host):
    service = host.service("prometheus")
    assert service.is_running
    assert service.is_enabled

def test_prometheus_listening(host):
    assert host.socket('tcp://0.0.0.0:9090').is_listening

def test_prometheus_scrape_target_file_exists(host):
    assert host.file('/etc/prometheus/targets/node_exporter.yml').exists

def test_prometheus_config_file_exists(host):
    assert host.file('/etc/prometheus/prometheus.yml').exists

def test_prometheus_binary_exists(host):
    assert host.exists('prometheus')

def test_prometheus_metrics_available(host):
    host.run_expect([0], 'curl localhost:9090/metrics')
```

See? That wasn't too hard was it?

We're using the `host` parameter in the functions to reference the Vagrant box. Using this reference we can then use the `testinfra` [modules](http://testinfra.readthedocs.io/en/latest/modules.html)
to ask all kind of information about the system.

If we want to hook the tests up to our `kitchen` test suite we'll have to go into the `.kitchen.yml` file and add a suite.
```yaml
suites:
  - name: prometheus
    provisioner:
      # Make sure to set the right grains as you would in production to ensure the right salt states being run
      grains:
        server_role:
          - prometheus
    # Now hook up the tests you've just written to a verifier
    verifier:
      name: shell
      command: py.test -v test/prometheus/
```

We can now test this suite by running `kitchen test prometheus`. Or we can decide to iterate on our states as thus:
```
$ kitchen create prometheus
$ kitchen converge prometheus
$ kitchen verify prometheus
$ # work on your states...
$ kitchen converge prometheus # apply them again
$ kitchen verify prometheus # run tests again
```

## Contributing

See the [CONTRIBUTING.md](CONTRIBUTING.md) file on how to contribute to this project.

## Contributors

See the [CONTRIBUTORS.md](CONTRIBUTORS.md) file for a list of contributors to the project.


## Changelog

The changelog can be found in the [CHANGELOG.md](CHANGELOG.md) file.

## Get in touch with a developer

If you want to report an issue see the [CONTRIBUTING.md](CONTRIBUTING.md) file for more info.

We will be happy to answer your other questions at [opensource@wearespindle.com](mailto:opensource@wearespindle.com)

## License

saltstack-testing is made available under the MIT license. See the [LICENSE file](LICENSE) for more info.
