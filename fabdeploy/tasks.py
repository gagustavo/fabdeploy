# -*- coding: utf-8 -*-

import os
from fabric.api import cd, env, get, local, run
from fabric.tasks import Task


class CustomTask(Task):

    name = None
    usage = None
    required_attributes = ()

    def __init__(self, *args, **kwargs):
        super(CustomTask, self).__init__(*args, **kwargs)
        self.ensure_attributes()

    def ensure_attributes(self):
        for attr in self.required_attributes:
            if not hasattr(self, attr):
                self.terminate(u'É necessário definir o atributo "{attr}" da classe base'.format(attr=attr))

    def terminate(self, message=None):
        if message:
            print(message)
        print('Usage: ' + self.usage)
        exit(1)


class RemoteTask(CustomTask):

    '''
    base_dir = '/var/www/projeto.com.br/'
    remote_hosts = {
        'homologacao': 'usuario@homologacao.projeto.com.br',
        'producao': 'usuario@projeto.com.br',
    }
    '''

    required_attributes = ('base_dir', 'remote_hosts')

    def set_host(self, host):
        host_string = self.remote_hosts.get(host)
        if not host_string:
            self.terminate('Error: Unknown host "{host}"'.format(host=host))
        env.host_string = host_string


class Deploy(RemoteTask):

    name = 'deploy'
    usage = 'fab deploy:<host>[,<commit>][,<build>=1]'

    commands = []
    commit_map = {
        'producao': 'origin/master',
        'homologacao': 'origin/homologacao',
    }

    '''
    prefix = 'pj_'
    project_name = 'projeto'
    '''

    required_attributes = ('prefix', 'project_name')

    def run(self, host=None, commit=None, build=False):
        self.set_host(host)
        self.setup(host, commit)
        self.push_changes()
        with cd(self.dest_dir):
            self.save_state()
            self.change_state()
            if build:
                self.rebuild_container()
            self.update_app()

    def setup(self, host, commit):
        self.commit = commit or self.commit_map.get(host)
        # Prefixo adicionado para tornar o nome dos containers mais claros
        self.dest_dir = os.path.join(self.base_dir, self.prefix + host)
        self.manifest = host + '.yml'

    def push_changes(self):
        local('git push ssh://{host}/~/{project_name}.git --all --force'.format(host=env.host_string, project_name=self.project_name))

    def save_state(self):
        try:
            run('git add -A .')
            run('git stash save')
        except:
            pass

    def change_state(self):
        run('git fetch origin')
        run('git checkout {commit}'.format(commit=self.commit))

    def rebuild_container(self):
        run('docker-compose -f {manifest} build'.format(manifest=self.manifest))

    def update_app(self):
        for cmd in self.commands:
            run('docker-compose -f {manifest} run web {command}'.format(command=cmd, manifest=self.manifest))
        run('docker-compose -f {manifest} up -d'.format(manifest=self.manifest))
