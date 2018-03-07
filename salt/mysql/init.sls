mysql-server:
  pkg.installed

mysql-service:
  service.running:
    - name: mysql
    {% if salt['pillar.get']('mysql:enabled') %}
    - enable: True
    {% endif %}