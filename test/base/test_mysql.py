def test_mysql_service_running(host):
    service = host.service('mysql')
    assert service.is_running
    assert service.is_enabled

def test_mysql_is_listening(host):
    assert host.socket('tcp://127.0.0.1:3306').is_listening