import functools
import os
import pytest
import testinfra

test_host = testinfra.get_host('paramiko://{KITCHEN_USERNAME}@{KITCHEN_HOSTNAME}:{KITCHEN_PORT}'.format(**os.environ), ssh_identity_file=os.environ.get('KITCHEN_SSH_KEY'))

@pytest.fixture
def host():
    return test_host

@pytest.fixture
def salt():
    test_host.run('sudo chown -R {0} /tmp/kitchen'.format(os.environ.get('KITCHEN_USERNAME')))
    tmpconf = '/tmp/kitchen/etc/salt'
    return functools.partial(test_host.salt, config=tmpconf)
