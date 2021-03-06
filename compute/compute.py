#   Copyright 2012-2013 STACKOPS TECHNOLOGIES S.L.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
from fabric.api import *
from cuisine import *

import fabuloso.utils as utils

import sys

PAGE_SIZE = 2 * 1024 * 1024
BONUS_PAGES = 40

NOVA_COMPUTE_CONF = '/etc/nova/nova-compute.conf'

NOVA_CONF = '/etc/nova/nova.conf'

DEFAULT_LIBVIRT_BIN_CONF = '/etc/default/libvirt-bin'

LIBVIRT_BIN_CONF = '/etc/init/libvirt-bin.conf'

LIBVIRTD_CONF = '/etc/libvirt/libvirtd.conf'

LIBVIRT_QEMU_CONF = '/etc/libvirt/qemu.conf'

COMPUTE_API_PASTE_CONF = '/etc/nova/api-paste.ini'

NEUTRON_API_PASTE_CONF = '/etc/neutron/api-paste.ini'

OVS_PLUGIN_CONF = '/etc/neutron/plugins/openvswitch/ovs_neutron_plugin.ini'

ML2_PLUGIN_CONF = '/etc/neutron/plugins/ml2/ml2_conf.ini'

NEUTRON_CONF = '/etc/neutron/neutron.conf'

NOVA_INSTANCES = '/var/lib/nova/instances'

NOVA_VOLUMES = '/var/lib/nova/volumes'


def stop():
    with settings(warn_only=True):
        openvswitch_stop()
        neutron_plugin_openvswitch_agent_stop()
        ntp_stop()
        compute_stop()
        iscsi_initiator_stop()


def start():
    stop()
    ntp_start()
    iscsi_initiator_start()
    openvswitch_start()
    neutron_plugin_openvswitch_agent_start()
    compute_start()


def openvswitch_stop():
    with settings(warn_only=True):
        sudo("/etc/init.d/openvswitch-switch stop")


def openvswitch_start():
    openvswitch_stop()
    sudo("/etc/init.d/openvswitch-switch start")


def neutron_plugin_openvswitch_agent_stop():
    with settings(warn_only=True):
        sudo("service neutron-plugin-openvswitch-agent stop")


def neutron_plugin_openvswitch_agent_start():
    neutron_plugin_openvswitch_agent_stop()
    sudo("service neutron-plugin-openvswitch-agent start")


def ntp_stop():
    with settings(warn_only=True):
        sudo("service ntp stop")


def ntp_start():
    ntp_stop()
    sudo("service ntp start")


def iscsi_initiator_stop():
    with settings(warn_only=True):
        sudo("nohup service open-iscsi stop")


def iscsi_initiator_start():
    iscsi_initiator_stop()
    sudo("nohup service open-iscsi start")


def compute_stop():
    with settings(warn_only=True):
        sudo("nohup service libvirt-bin stop")
    with settings(warn_only=True):
        sudo("nohup service nova-compute stop")


def compute_start():
    compute_stop()
    sudo("nohup service libvirt-bin start")
    sudo("nohup service nova-compute start")


def configure_ubuntu_packages():
    """Configure compute packages"""
    package_ensure('vlan')
    package_ensure('bridge-utils')
    package_ensure('python-amqp')
    package_ensure('python-guestfs')
    package_ensure('python-software-properties')
    package_ensure('ntp')
    package_ensure('pm-utils')
    package_ensure('nova-compute-kvm')
    package_ensure('neutron-plugin-openvswitch-agent')
    package_ensure('openvswitch-switch')
    package_ensure('openvswitch-datapath-dkms')
    package_ensure('open-iscsi')
    package_ensure('autofs')


def uninstall_ubuntu_packages():
    """Uninstall compute packages"""
    package_clean('python-amqp')
    package_clean('python-guestfs')
    package_clean('python-software-properties')
    package_clean('ntp')
    package_clean('pm-utils')
    package_clean('nova-compute-kvm')
    package_clean('neutron-plugin-openvswitch-agent')
    package_clean('openvswitch-switch')
    package_clean('openvswitch-datapath-dkms')
    package_clean('open-iscsi')
    package_clean('autofs')
    package_clean('vlan')
    package_clean('bridge-utils')


def install():
    """Generate compute configuration. Execute on both servers"""
    sudo('chmod 0644 /boot/vmlinuz*')
    configure_ubuntu_packages()
    sudo('update-rc.d neutron-plugin-openvswitch-agent defaults 98 02')
    sudo('update-rc.d nova-compute defaults 98 02')


def configure_forwarding():
    sudo("sed -i -r 's/^\s*#(net\.ipv4\.ip_forward=1.*)"
         "/\\1/' /etc/sysctl.conf")
    sudo("echo 1 > /proc/sys/net/ipv4/ip_forward")


def configure_ntp():
    sudo('echo "server automation" > /etc/ntp.conf')


def configure_vhost_net():
    sudo('modprobe vhost-net')
    sudo("sed -i '/modprobe vhost-net/d' /etc/rc.local")
    sudo("sed -i '/exit 0/d' /etc/rc.local")
    sudo("echo 'modprobe vhost-net' >> /etc/rc.local")
    sudo("echo 'exit 0' >> /etc/rc.local")


def configure_libvirt(hostname, shared_storage=False,
                      instances_path='/var/lib/nova/instances'):
    utils.uncomment_property(LIBVIRT_QEMU_CONF, 'cgroup_device_acl')
    utils.modify_property(LIBVIRT_QEMU_CONF,
                          'cgroup_device_acl',
                          '["/dev/null", "/dev/full", "/dev/zero", '
                          '"/dev/random", "/dev/urandom", "/dev/ptmx", '
                          '"/dev/kvm", "/dev/kqemu", "/dev/rtc", "/dev/hpet"'
                          ',"/dev/net/tun"]')
    utils.uncomment_property(LIBVIRTD_CONF, 'listen_tls')
    utils.uncomment_property(LIBVIRTD_CONF, 'listen_tcp')
    utils.uncomment_property(LIBVIRTD_CONF, 'auth_tcp')
    utils.modify_property(LIBVIRTD_CONF, 'listen_tls', '0')
    utils.modify_property(LIBVIRTD_CONF, 'listen_tcp', '1')
    utils.modify_property(LIBVIRTD_CONF, 'auth_tcp', '"none"')
    utils.modify_property(LIBVIRT_BIN_CONF, 'env libvirtd_opts', '"-d -l"')
    utils.modify_property(DEFAULT_LIBVIRT_BIN_CONF, 'libvirtd_opts', '"-d -l"')
    with settings(warn_only=True):
        sudo('virsh net-destroy default')
        sudo('virsh net-undefine default')

    compute_stop()
    # share libvirt configuration to restore compute nodes
    if shared_storage:
        path = '%s/libvirt/%s' % (instances_path, hostname)
        if not dir_exists(path):
            sudo('mkdir -p %s' % path)
            sudo('cp -fR /etc/libvirt/* %s/' % path)
        dir_remove('/etc/libvirt')
        sudo('ln -s %s /etc/libvirt' % path)
    compute_start()


def set_config_file(management_ip=None, controller_host=None, vncproxy_host=None, auth_host=None, nova_mysql_host=None,
                    glance_host=None, rabbit_host=None, rabbit_password='guest',
                    nova_mysql_username='nova',
                    nova_mysql_password='stackops', nova_mysql_port='3306', nova_mysql_schema='nova',
                    nova_service_user='nova', nova_service_tenant='service', nova_service_pass='stackops',
                    auth_port='35357', auth_protocol='http', libvirt_type='kvm', vncproxy_protocol="https", vncproxy_port='6080',
                    glance_port='9292'):
    if controller_host is None:
        puts("{error:'Management IP of the node needed as argument'}")
        exit(0)

    neutron_url = 'http://%s:9696' % controller_host
    admin_auth_url = 'http://%s:35357/v2.0' % auth_host
    vncproxy_url = '%s://%s:%s/vnc_auto.html' % (vncproxy_protocol, vncproxy_host, vncproxy_port)
    auth_host = auth_host
    mysql_host = nova_mysql_host
    glance_host = glance_host
    rabbit_host = rabbit_host

    utils.set_option(COMPUTE_API_PASTE_CONF, 'admin_tenant_name', nova_service_tenant, section='filter:authtoken')
    utils.set_option(COMPUTE_API_PASTE_CONF, 'admin_user', nova_service_user, section='filter:authtoken')
    utils.set_option(COMPUTE_API_PASTE_CONF, 'admin_password', nova_service_pass, section='filter:authtoken')
    utils.set_option(COMPUTE_API_PASTE_CONF, 'auth_host', auth_host, section='filter:authtoken')
    utils.set_option(COMPUTE_API_PASTE_CONF, 'auth_port', auth_port, section='filter:authtoken')
    utils.set_option(COMPUTE_API_PASTE_CONF, 'auth_protocol', auth_protocol, section='filter:authtoken')

    utils.set_option(NOVA_COMPUTE_CONF, 'sql_connection',
                     utils.sql_connect_string(nova_mysql_host, nova_mysql_password, nova_mysql_port, nova_mysql_schema, nova_mysql_username))
    utils.set_option(NOVA_COMPUTE_CONF, 'verbose', 'true')
    utils.set_option(NOVA_COMPUTE_CONF, 'auth_strategy', 'keystone')
    utils.set_option(NOVA_COMPUTE_CONF, 'use_deprecated_auth', 'false')
    utils.set_option(NOVA_COMPUTE_CONF, 'logdir', '/var/log/nova')
    utils.set_option(NOVA_COMPUTE_CONF, 'state_path', '/var/lib/nova')
    utils.set_option(NOVA_COMPUTE_CONF, 'lock_path', '/var/lock/nova')
    utils.set_option(NOVA_COMPUTE_CONF, 'root_helper', 'sudo nova-rootwrap /etc/nova/rootwrap.conf')
    utils.set_option(NOVA_COMPUTE_CONF, 'verbose', 'true')
    utils.set_option(NOVA_COMPUTE_CONF, 'rpc_backend', 'nova.rpc.impl_kombu')
    utils.set_option(NOVA_COMPUTE_CONF, 'rabbit_host', rabbit_host)
    utils.set_option(NOVA_COMPUTE_CONF, 'rabbit_password', rabbit_password)
    utils.set_option(NOVA_COMPUTE_CONF, 'notification_driver',
                     'nova.openstack.common.notifier.rpc_notifier')
    utils.set_option(NOVA_COMPUTE_CONF, 'notification_topics',
                     'notifications,monitor')
    utils.set_option(NOVA_COMPUTE_CONF, 'default_notification_level', 'INFO')
    utils.set_option(NOVA_COMPUTE_CONF, 'my_ip', management_ip)
    utils.set_option(NOVA_COMPUTE_CONF, 'connection_type', 'libvirt')
    utils.set_option(NOVA_COMPUTE_CONF, 'libvirt_type', libvirt_type)
    utils.set_option(NOVA_COMPUTE_CONF, 'libvirt_ovs_bridge', 'br-int')
    utils.set_option(NOVA_COMPUTE_CONF, 'libvirt_vif_type', 'ethernet')
    utils.set_option(NOVA_COMPUTE_CONF, 'libvirt_vif_driver',
                     'nova.virt.libvirt.vif.LibvirtGenericVIFDriver')
    utils.set_option(NOVA_COMPUTE_CONF, 'libvirt_use_virtio_for_bridges',
                     'true')
    utils.set_option(NOVA_COMPUTE_CONF, 'neutron_auth_strategy',
                     'keystone')
    utils.set_option(NOVA_COMPUTE_CONF, 'neutron_admin_username',
                     'neutron')
    utils.set_option(NOVA_COMPUTE_CONF, 'neutron_admin_password',
                     'stackops')
    utils.set_option(NOVA_COMPUTE_CONF, 'neutron_admin_tenant_name',
                     'service')
    utils.set_option(NOVA_COMPUTE_CONF, 'neutron_admin_auth_url',
                     admin_auth_url)
    utils.set_option(NOVA_COMPUTE_CONF, 'neutron_url',
                     neutron_url)
    utils.set_option(NOVA_COMPUTE_CONF, 'novncproxy_base_url', vncproxy_url)
    utils.set_option(NOVA_COMPUTE_CONF, 'vncserver_listen', '0.0.0.0')
    utils.set_option(NOVA_COMPUTE_CONF, 'vnc_enabled', 'true')
    utils.set_option(NOVA_COMPUTE_CONF, 'vncserver_proxyclient_address',
                     management_ip)

    utils.set_option(NOVA_COMPUTE_CONF, 'compute_driver',
                      'libvirt.LibvirtDriver')

    utils.set_option(NOVA_COMPUTE_CONF, 'image_service',
                     'nova.image.glance.GlanceImageService')
    utils.set_option(NOVA_COMPUTE_CONF, 'glance_api_servers',
                     '%s:%s' % (glance_host, glance_port))
    utils.set_option(NOVA_COMPUTE_CONF, 'glance_host', glance_host)
    # Change for havana to use the neutron fw and security group
    utils.set_option(NOVA_COMPUTE_CONF, 'firewall_driver',
                     'nova.virt.firewall.NoopFirewallDriver')
    utils.set_option(NOVA_COMPUTE_CONF, 'security_group_api', 'neutron')
    utils.set_option(NOVA_COMPUTE_CONF, 'ec2_private_dns_show_ip', 'True')
    utils.set_option(NOVA_COMPUTE_CONF, 'network_api_class',
                     'nova.network.neutronv2.api.API')
    utils.set_option(NOVA_COMPUTE_CONF, 'dmz_cidr', '169.254.169.254/32')
    utils.set_option(NOVA_COMPUTE_CONF, 'volume_api_class',
                     'nova.volume.cinder.API')
    utils.set_option(NOVA_COMPUTE_CONF, 'cinder_catalog_info',
                     'volume:cinder:internalURL')

    utils.set_option(NOVA_COMPUTE_CONF, 'allow_same_net_traffic',
                     'True')
    utils.set_option(NOVA_COMPUTE_CONF, 'allow_resize_to_same_host', 'True')
    utils.set_option(NOVA_COMPUTE_CONF, 'resize_confirm_window', '3600')
    utils.set_option(NOVA_COMPUTE_CONF, 'snapshot_compression', 'True')
    utils.set_option(NOVA_COMPUTE_CONF, 'snapshot_image_format', 'qcow2')
    utils.set_option(NOVA_COMPUTE_CONF, 'start_guests_on_host_boot', 'false')
    utils.set_option(NOVA_COMPUTE_CONF, 'resume_guests_state_on_host_boot', 'true')

    start()


def configure_neutron(neutron_service_user='neutron', neutron_service_password='stackops',
                      auth_host='127.0.0.1', auth_port='35357',
                      auth_protocol='http', neutron_service_tenant='service',
                      rabbit_password='guest', rabbit_host='127.0.0.1',
                      neutron_mysql_username='neutron',
                      neutron_mysql_password='stackops',
                      neutron_mysql_schema='neutron', mysql_host='127.0.0.1',
                      mysql_port='3306'):
    cp = 'neutron.plugins.ml2.plugin.Ml2Plugin'
    utils.set_option(NEUTRON_CONF, 'core_plugin', cp)
    utils.set_option(NEUTRON_CONF, 'auth_strategy', 'keystone')
    utils.set_option(NEUTRON_CONF, 'fake_rabbit', 'False')
    utils.set_option(NEUTRON_CONF, 'rabbit_password', rabbit_password)
    utils.set_option(NEUTRON_CONF, 'rabbit_host', rabbit_host)
    utils.set_option(NEUTRON_CONF, 'notification_driver',
                     'nova.openstack.common.notifier.rpc_notifier')
    utils.set_option(NEUTRON_CONF, 'notification_topics',
                     'notifications,monitor')
    utils.set_option(NEUTRON_CONF, 'default_notification_level', 'INFO')
    utils.set_option(NEUTRON_CONF, 'connection', utils.sql_connect_string(
        mysql_host, neutron_mysql_password, mysql_port, neutron_mysql_schema, neutron_mysql_username),
                     section='database')
    utils.set_option(NEUTRON_CONF, 'admin_tenant_name',
                     neutron_service_tenant, section='keystone_authtoken')
    utils.set_option(NEUTRON_CONF, 'admin_user',
                     neutron_service_user, section='keystone_authtoken')
    utils.set_option(NEUTRON_CONF, 'admin_password',
                     neutron_service_password, section='keystone_authtoken')
    utils.set_option(NEUTRON_CONF, 'auth_host', auth_host,
                     section='keystone_authtoken')
    utils.set_option(NEUTRON_CONF, 'auth_port', auth_port,
                     section='keystone_authtoken')
    utils.set_option(NEUTRON_CONF, 'auth_protocol', auth_protocol,
                     section='keystone_authtoken')
    auth_uri = 'http://' + auth_host + ':5000/v2.0'
    utils.set_option(NEUTRON_CONF, 'auth_url', auth_uri,
                     section='keystone_authtoken')
    utils.set_option(NEUTRON_API_PASTE_CONF, 'admin_tenant_name',
                     neutron_service_tenant, section='filter:authtoken')
    utils.set_option(NEUTRON_API_PASTE_CONF, 'admin_user',
                     neutron_service_user, section='filter:authtoken')
    utils.set_option(NEUTRON_API_PASTE_CONF, 'admin_password',
                     neutron_service_password, section='filter:authtoken')
    utils.set_option(NEUTRON_API_PASTE_CONF, 'auth_host', auth_host,
                     section='filter:authtoken')
    utils.set_option(NEUTRON_API_PASTE_CONF, 'auth_port',
                     auth_port, section='filter:authtoken')
    utils.set_option(NEUTRON_API_PASTE_CONF, 'auth_protocol',
                     auth_protocol, section='filter:authtoken')
    neutron_plugin_openvswitch_agent_start()


def configure_ovs_plugin_gre(local_ip=None, neutron_mysql_username='neutron',
                             neutron_mysql_password='stackops',
                             neutron_mysql_host='127.0.0.1', neutron_mysql_port='3306',
                             neutron_mysql_schema='neutron'):
    utils.set_option(OVS_PLUGIN_CONF, 'sql_connection',
                     utils.sql_connect_string(neutron_mysql_host, neutron_mysql_password,
                                              neutron_mysql_port, neutron_mysql_schema,
                                              neutron_mysql_username),
                     section='DATABASE')
    utils.set_option(OVS_PLUGIN_CONF, 'reconnect_interval', '2',
                     section='DATABASE')
    utils.set_option(OVS_PLUGIN_CONF, 'tenant_network_type', 'gre',
                     section='OVS')
    utils.set_option(OVS_PLUGIN_CONF, 'tunnel_id_ranges', '1:1000',
                     section='OVS')
    utils.set_option(OVS_PLUGIN_CONF, 'local_ip', local_ip,
                     section='OVS')
    utils.set_option(OVS_PLUGIN_CONF, 'integration_bridge', 'br-int',
                     section='OVS')
    utils.set_option(OVS_PLUGIN_CONF, 'tunnel_bridge', 'br-tun',
                     section='OVS')
    utils.set_option(OVS_PLUGIN_CONF, 'enable_tunneling', 'True',
                     section='OVS')
    utils.set_option(OVS_PLUGIN_CONF, 'root_helper',
                     'sudo neutron-rootwrap '
                     '/etc/neutron/rootwrap.conf', section='AGENT')
    #utils.set_option(OVS_PLUGIN_CONF, 'firewall_driver',
    #                 'neutron.agent.linux.iptables_firewall.'
    #                 'OVSHybridIptablesFirewallDriver',
    # section='securitygroup')
    with settings(warn_only=True):
        sudo('ovs-vsctl del-br br-int')
    sudo('ovs-vsctl add-br br-int')
    openvswitch_start()
    neutron_plugin_openvswitch_agent_start()


def configure_ml2_plugin_vxlan(neutron_mysql_username='neutron',
                               neutron_mysql_password='stackops',
                               neutron_mysql_host='127.0.0.1', neutron_mysql_port='3306',
                               neutron_mysql_schema='neutron',
                               local_ip='127.0.0.1'):
    # TODO Fix that when ml2-neutron-plugin will be added in icehouse
    sudo('mkdir -p /etc/neutron/plugins/ml2')
    with settings(warn_only=True):
        sudo('ln -s %s %s' % (OVS_PLUGIN_CONF, ML2_PLUGIN_CONF))
    sudo('echo "''" > %s' % OVS_PLUGIN_CONF)
    sudo('echo [ml2] >> %s' % OVS_PLUGIN_CONF)
    sudo('echo [ovs] >> %s' % OVS_PLUGIN_CONF)
    sudo('echo [ml2_type_vxlan] >> %s' % OVS_PLUGIN_CONF)
    sudo('echo [database] >> %s' % OVS_PLUGIN_CONF)
    sudo('echo [securitygroup] >> %s' % OVS_PLUGIN_CONF)
    sudo('echo [agent] >> %s' % OVS_PLUGIN_CONF)
    # ML2 section
    utils.set_option(OVS_PLUGIN_CONF, 'tenant_network_types', 'vxlan',
                     section='ml2')
    utils.set_option(OVS_PLUGIN_CONF, 'type_drivers',
                     'local,flat,vlan,gre,vxlan', section='ml2')
    utils.set_option(OVS_PLUGIN_CONF, 'mechanism_drivers',
                     'openvswitch,linuxbridge', section='ml2')
    # ml2_type_vxlan section
    utils.set_option(OVS_PLUGIN_CONF, 'vni_ranges', '1:1000',
                     section='ml2_type_vxlan')
    # ovs section
    utils.set_option(OVS_PLUGIN_CONF, 'local_ip', local_ip, section='ovs')
    utils.set_option(OVS_PLUGIN_CONF, 'enable_tunneling', 'True',
                     section='ovs')
    # database section
    utils.set_option(OVS_PLUGIN_CONF, 'connection',
                     utils.sql_connect_string(neutron_mysql_host, neutron_mysql_password,
                                              neutron_mysql_port, neutron_mysql_schema,
                                              neutron_mysql_username),
                     section='database')
    # security group section
    utils.set_option(OVS_PLUGIN_CONF, 'firewall_driver',
                     'neutron.agent.linux.iptables_firewall.'
                     'OVSHybridIptablesFirewallDriver',
                     section='securitygroup')
    # agent section
    utils.set_option(OVS_PLUGIN_CONF, 'root_helper',
                     'sudo neutron-rootwrap '
                     '/etc/neutron/rootwrap.conf', section='agent')
    utils.set_option(OVS_PLUGIN_CONF, 'tunnel_types', 'vxlan',
                     section='agent')
    with settings(warn_only=True):
        sudo('ovs-vsctl del-br br-int')
    sudo('ovs-vsctl add-br br-int')
    neutron_plugin_openvswitch_agent_start()


def configure_ml2_plugin_vlan(br_postfix='bond-vm', vlan_start='2',
                              vlan_end='4094', neutron_mysql_username='neutron',
                              neutron_mysql_password='stackops',
                              neutron_mysql_host='127.0.0.1', neutron_mysql_port='3306',
                              neutron_mysql_schema='neutron'):
    # TODO Fix that when ml2-neutron-plugin will be added in icehouse
    sudo('mkdir -p /etc/neutron/plugins/ml2')
    sudo('ln -s %s %s' % (OVS_PLUGIN_CONF, ML2_PLUGIN_CONF))
    sudo('echo "''" > %s' % OVS_PLUGIN_CONF)
    sudo('echo [ml2] >> %s' % OVS_PLUGIN_CONF)
    sudo('echo [ovs] >> %s' % OVS_PLUGIN_CONF)
    sudo('echo [ml2_type_vlan] >> %s' % OVS_PLUGIN_CONF)
    sudo('echo [database] >> %s' % OVS_PLUGIN_CONF)
    sudo('echo [securitygroup] >> %s' % OVS_PLUGIN_CONF)
    sudo('echo [agent] >> %s' % OVS_PLUGIN_CONF)
    # ML2 section
    utils.set_option(OVS_PLUGIN_CONF, 'tenant_network_types', 'vlan',
                     section='ml2')
    utils.set_option(OVS_PLUGIN_CONF, 'type_drivers',
                     'local,flat,vlan,gre,vxlan', section='ml2')
    utils.set_option(OVS_PLUGIN_CONF, 'mechanism_drivers',
                     'openvswitch,linuxbridge', section='ml2')
    # ml2_type_vlan section
    utils.set_option(OVS_PLUGIN_CONF, 'network_vlan_ranges', 'physnet1:%s:%s'
                                                             % (vlan_start, vlan_end), section='ml2_type_vlan')
    utils.set_option(OVS_PLUGIN_CONF, 'bridge_mappings',
                     'physnet1:br-%s' % br_postfix, section='ovs')
    # database section
    utils.set_option(OVS_PLUGIN_CONF, 'connection',
                     utils.sql_connect_string(neutron_mysql_host, neutron_mysql_password,
                                              neutron_mysql_port, neutron_mysql_schema,
                                              neutron_mysql_username),
                     section='database')
    # security group section
    utils.set_option(OVS_PLUGIN_CONF, 'firewall_driver',
                     'neutron.agent.linux.iptables_firewall.'
                     'OVSHybridIptablesFirewallDriver',
                     section='securitygroup')
    # agent section
    utils.set_option(OVS_PLUGIN_CONF, 'root_helper',
                     'sudo neutron-rootwrap '
                     '/etc/neutron/rootwrap.conf', section='agent')
    with settings(warn_only=True):
        sudo('ovs-vsctl del-br br-int')
    sudo('ovs-vsctl add-br br-int')
    neutron_plugin_openvswitch_agent_start()


def configure_nfs_storage(nfs_server, delete_content=False,
                          set_nova_owner=True,
                          nfs_server_mount_point_params='defaults'):
    package_ensure('nfs-common')
    package_ensure('autofs')
    utils.set_option(NOVA_COMPUTE_CONF, 'libvirt_images_type', 'default')
    if delete_content:
        sudo('rm -fr %s' % NOVA_INSTANCES)
    stop()
    nova_instance_exists = file_exists(NOVA_INSTANCES)
    if not nova_instance_exists:
        sudo('mkdir -p %s' % NOVA_INSTANCES)
    mpoint = '%s  -fstype=nfs,vers=3,%s   %s' % \
             (NOVA_INSTANCES, nfs_server_mount_point_params, nfs_server)
    sudo('''echo "/-    /etc/auto.nfs" > /etc/auto.master''')
    sudo('''echo "%s" > /etc/auto.nfs''' % mpoint)
    sudo('service autofs restart')
    with settings(warn_only=True):
        if set_nova_owner:
            if not nova_instance_exists:
                sudo('chown nova:nova -R %s' % NOVA_INSTANCES)
    start()


def configure_local_storage(delete_content=False, set_nova_owner=True):
    utils.set_option(NOVA_COMPUTE_CONF, 'libvirt_images_type', 'default')
    if delete_content:
        sudo('rm -fr %s' % NOVA_INSTANCES)
    stop()
    sudo('sed -i "#%s#d" /etc/fstab' % NOVA_INSTANCES)
    sudo('mkdir -p %s' % NOVA_INSTANCES)
    if set_nova_owner:
        sudo('chown nova:nova -R %s' % NOVA_INSTANCES)
    start()


def create_volume(partition='/dev/sdb1', name='nova-volume'):
    sudo('pvcreate %s' % partition)
    sudo('vgcreate %s %s' % (name, partition))


def configure_lvm_storage(name='nova-volume', sparse='False'):
    utils.set_option(NOVA_COMPUTE_CONF, 'libvirt_images_type', 'lvm')
    utils.set_option(NOVA_COMPUTE_CONF, 'libvirt_images_volume_group', name)
    utils.set_option(NOVA_COMPUTE_CONF, 'libvirt_sparse_logical_volumes', sparse)
    start()


def set_option(property='', value=''):
    utils.set_option(NOVA_COMPUTE_CONF, property, value)


def configure_nfs_volumes(delete_content=False,
                          set_nova_owner=True):
    package_ensure('nfs-common')
    package_ensure('autofs')
    utils.set_option(NOVA_COMPUTE_CONF, 'nfs_mount_point_base', NOVA_VOLUMES)
    if delete_content:
        sudo('rm -fr %s' % NOVA_VOLUMES)
    stop()
    nova_volumes_exists = file_exists(NOVA_VOLUMES)
    if not nova_volumes_exists:
        sudo('mkdir -p %s' % NOVA_VOLUMES)
    with settings(warn_only=True):
        if set_nova_owner:
            if not nova_volumes_exists:
                sudo('chown nova:nova -R %s' % NOVA_VOLUMES)
    start()


def configure_rescue_image(uuid=None):
    stop()
    utils.set_option(NOVA_COMPUTE_CONF, 'rescue_image_id', uuid)
    start()

def configure_snapshots(snapshot_compression='True', snapshot_image_format='qcow2'):
    stop()
    utils.set_option(NOVA_COMPUTE_CONF, 'snapshot_compression', 'True')
    utils.set_option(NOVA_COMPUTE_CONF, 'snapshot_image_format', 'qcow2')
    start()

def configure_network(iface_bridge='eth0 eth1', br_postfix='bond0',
                      management_bridge="br-mgmt", vxlan_bridge="br-vxlan",
                      bond_parameters='bond_mode=balance-slb '
                                      'other_config:bond-detect-mode=miimon '
                                      'other_config:bond-miimon-interval=100',
                      network_restart=False):
    # Disable packet destination filter
    sudo("sed -i -r 's/^\s*#(net\.ipv4\.conf\.all\.rp_filter=1.*)"
         "/\\0/' /etc/sysctl.conf")
    sudo("sed -i -r 's/^\s*#(net\.ipv4\.conf\.default\.rp_filter=1.*)"
         "/\\0/' /etc/sysctl.conf")
    openvswitch_start()
    #configure_forwarding()
    try:
        command = ""
        with settings(warn_only=True):
            command += 'ovs-vsctl del-br br-%s; ' % br_postfix
        command += 'ovs-vsctl add-br br-%s; ' % br_postfix
        if management_bridge:
            command += 'ovs-vsctl add-port br-%s %s -- set interface %s type=internal; ' % (
                br_postfix, management_bridge, management_bridge)
        if vxlan_bridge:
            command += 'ovs-vsctl add-port br-%s %s -- set interface %s type=internal; ' % (
                br_postfix, vxlan_bridge, vxlan_bridge)
        if network_restart:
            command += 'ovs-vsctl add-bond br-%s %s %s %s; reboot' % (
                br_postfix, br_postfix, iface_bridge, bond_parameters)
        else:
            command += 'ovs-vsctl add-bond br-%s %s %s %s' % (br_postfix, br_postfix, iface_bridge, bond_parameters)
        sudo("echo '%s'" % command)
        sudo(command)
    except:
        print sys.exc_info()[0]
        raise


def configure_migrations(nova_pass="nova"):
    sudo("usermod -s /bin/bash nova")
    sudo("echo 'nova:%s'|chpasswd" % nova_pass)
    sudo("su nova -c 'rm -fR /var/lib/nova/.ssh'")
    sudo("su nova -c 'mkdir /var/lib/nova/.ssh'")
    sudo("su nova -c 'chmod 700 /var/lib/nova/.ssh'")
    sudo('''su nova -c 'echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC07jNnA1g7O7H7Ka+tbuQyiMn12IjtbGY+8RJrUU11jjlM3llZhJhyBgoNP864cOL37j0uVE+SxXfmxwY0glupX0KvgvS8dd9v0T0R04giS/eM4b1CGHAg/EquklA/WGQ/LHJtaQf8hUdjTo7EshY8k7c0LvixBC9dnaYxSg5bkpxDCIoZ9Z/eYkoJxyhw2/cxc/hxvprLsNC1uBCKCNlqhDF9+Qm+rTzeHfLmVJCmcjnrIERce0dqbxcI+e7sDGPS/kAYZpNg5rhEDOQbw8qly8vxNGM8vdMyKIokzatBWsd2NwqoFI4Kv59I2WvsTkpUE3yl+uyaXL42h+WEDuF1 contactus@stackops.com" > /var/lib/nova/.ssh/authorized_keys' ''')
    sudo('''su nova -c 'echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC07jNnA1g7O7H7Ka+tbuQyiMn12IjtbGY+8RJrUU11jjlM3llZhJhyBgoNP864cOL37j0uVE+SxXfmxwY0glupX0KvgvS8dd9v0T0R04giS/eM4b1CGHAg/EquklA/WGQ/LHJtaQf8hUdjTo7EshY8k7c0LvixBC9dnaYxSg5bkpxDCIoZ9Z/eYkoJxyhw2/cxc/hxvprLsNC1uBCKCNlqhDF9+Qm+rTzeHfLmVJCmcjnrIERce0dqbxcI+e7sDGPS/kAYZpNg5rhEDOQbw8qly8vxNGM8vdMyKIokzatBWsd2NwqoFI4Kv59I2WvsTkpUE3yl+uyaXL42h+WEDuF1 contactus@stackops.com" > /var/lib/nova/.ssh/id_rsa.pub' ''')
    sudo("su nova -c 'chmod 600 /var/lib/nova/.ssh/authorized_keys'")
    nonsecurekey = text_strip_margin('''
    |-----BEGIN RSA PRIVATE KEY-----
    |MIIEowIBAAKCAQEAtO4zZwNYOzux+ymvrW7kMojJ9diI7WxmPvESa1FNdY45TN5Z
    |WYSYcgYKDT/OuHDi9+49LlRPksV35scGNIJbqV9Cr4L0vHXfb9E9EdOIIkv3jOG9
    |QhhwIPxKrpJQP1hkPyxybWkH/IVHY06OxLIWPJO3NC74sQQvXZ2mMUoOW5KcQwiK
    |GfWf3mJKCccocNv3MXP4cb6ay7DQtbgQigjZaoQxffkJvq083h3y5lSQpnI56yBE
    |XHtHam8XCPnu7Axj0v5AGGaTYOa4RAzkG8PKpcvL8TRjPL3TMiiKJM2rQVrHdjcK
    |qBSOCr+fSNlr7E5KVBN8pfrsmly+NoflhA7hdQIDAQABAoIBAQCyz2rrlsmfGJsI
    |TyV48MwECV4XYt3IT0YpVFTQzPQRhvKoPmLtbna+0asjdvkVHTOitcevPtG5iwC5
    |id5fDKoMFMIx9OlsS837kz2YnYa/5nYLvJkvdjly0AP6zU0TnYbNTF72NEQZU5q+
    |0UeVqy8AxTfdEcLkJu+sxH4X3kmcQvhz2q7L2pbSgZ0JeL1Nfxmy0cjsSKEVy3qY
    |0tLVm4xHStoYNBpzgXyBqhz/wAhOcctUyl5qvpNzgR+ihASNRKYKIGcpjgjaSryk
    |0Gp8WmwrSuy1qQ8iqKRkSa5SSWqwl1umWlb1V8+7m4ic0A/GJEhzJ5pfXPMaOQuF
    |eHG60JNNAoGBAOyA1R1US5mjoaIZmahR2Rl6nYFQQy3HNqQy1AZU5hB4uTrMA2eW
    |sSxt1RMBjlE9C0sUOFB95w48/gZNI6JPdMFGgcux5WrndDruY8txiVl3rw2Dw7Ih
    |JMxNBsJRO0AZgijUm11HPBp/tJ4HjppZiqE0exjoNFGOLc/l4VOZ1PbDAoGBAMPY
    |j0dS7eHcsmu+v6EpxbRFwSyZG0eV51IiT0DFLfiSpsfmtHdA1ZQeqbVadM1WJSLu
    |ZJ8uvGNRnuLgz2vwKdI6kJFfWYZSS5jfnl874/OF6riNQDseX5CvB5zQvTFVmae+
    |Mld4x2NYFxQ1vIWnGITGQKhcZonBMyAjaQ9tAnNnAoGASvTOFpyX1VryKHEarSk7
    |uIKPFuP8Vq7z13iwkE0qGYBZnJP6ZENzZdRtmrd8hqzlPmdrLb+pkm6sSAz8xT2P
    |kI4rJwb74jT3NpJFmL4kPPHczli7lmJAymuDP+UE9VzgTtaLYzXni7J76TYV8T99
    |23fJp+w4YLzCMkj2cEuqHocCgYBb2KEBMwwqw4TNcOyP2XZFn/0DPF6FyPBuHXcL
    |ii2QCL68ux5hWv+O8n5mdaCXd9H8us5ntNRWw71+6y17kmsak6qe8peandekPyMX
    |yI+T8nbszBmWYB0zTlKEoYRIsbtY5qLXUOY5WeOg776U85NVGWDTVFomOnwOk2y+
    |9kGS+wKBgD3cL/zabIv/kK7KY84EdWdVH4sal3bRsiNn4ezj7go/ObMgR59O4Lr4
    |fYqT1igILotduz/knlkleY2fsqltStWYzRrG+/zNryIBco2+cIX8T120AnpbAvlP
    |gj0YVjuLJXSC9w/URFG+ZGg0kX0Koy1yS6fuxikiA4f5Lw9znjaD
    |-----END RSA PRIVATE KEY-----
    |''')
    file_write('/tmp/id_rsa', nonsecurekey, sudo=False)
    sudo("su nova -c 'cp /tmp/id_rsa /var/lib/nova/.ssh/id_rsa'")
    sudo("su nova -c 'chmod 600 /var/lib/nova/.ssh/id_rsa*'")
    sudo("echo '  StrictHostKeyChecking no' >> /etc/ssh/ssh_config")
