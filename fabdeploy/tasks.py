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
    remote_hosts = {
        'homologacao': 'usuario@homologacao.projeto.com.br',
        'producao': 'usuario@projeto.com.br',
    }
    '''

    required_attributes = ('remote_hosts',)

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
    container = 'web'

    '''
    base_dir = '/var/www/projeto.com.br/'
    prefix = 'pj_'
    project_name = 'projeto'
    '''

    required_attributes = ('base_dir', 'prefix', 'project_name')

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
        self.push_tags(self)

    def push_tags(self):
        local('git push ssh://{host}/~/{project_name}.git --tags --force'.format(host=env.host_string, project_name=self.project_name))

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
            run('docker-compose -f {manifest} run {container} {command}'.format(command=cmd, container=self.container, manifest=self.manifest))
        run('docker-compose -f {manifest} up -d'.format(manifest=self.manifest))


class DownloadDB(RemoteTask):

    name = 'download_db'
    usage = 'fab download_db:<host>'

    commands = []
    sql_file = '/tmp/dump.sql'
    compressed_dump = sql_file + '.bz2'
    db_host = 'postgresql.sisqualis.com.br'

    '''
    local_db = 'projeto_db'
    project_name = 'projeto'
    '''

    required_attributes = ('local_db', 'project_name')

    def run(self, host=None):
        self.set_host(host)
        self.dump_db(host)
        self.compress_dump()
        self.download_dump()
        self.extract_dump()
        self.import_dump()

    def compress_dump(self):
        run('pbzip2 -f {sql_file}'.format(sql_file=self.sql_file))

    def download_dump(self):
        get(self.compressed_dump, self.compressed_dump)

    def dump_db(self, host):
        run('pg_dump -U {project_name}_{host} -h {db_host} --no-acl --no-owner {project_name}_{host} > {sql_file}'.format(
                host=host,
                project_name=self.project_name,
                sql_file=self.sql_file,
                db_host=self.db_host,
            )
        )

    def extract_dump(self):
        local('bunzip2 -f {compressed_dump}'.format(compressed_dump=self.compressed_dump))

    def import_dump(self):
        local('dropdb -U postgres {local_db}'.format(local_db=self.local_db))
        local('createdb -U postgres {local_db}'.format(local_db=self.local_db))
        local('psql -U postgres {local_db} -f {sql_file}'.format(local_db=self.local_db, sql_file=self.sql_file))

        for cmd in self.commands:
            local(cmd)
