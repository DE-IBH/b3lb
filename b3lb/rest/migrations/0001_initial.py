# Generated by Django 3.1.7 on 2021-02-24 22:05

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import rest.models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Cluster',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('name', models.CharField(help_text='cluster name', max_length=100, unique=True)),
                ('load_a_factor', models.FloatField(default=1.0, help_text='per attendee load factor')),
                ('load_m_factor', models.FloatField(default=30.0, help_text='per meeting load factor')),
                ('load_cpu_iterations', models.IntegerField(default=6, help_text='max sum iteration')),
                ('load_cpu_max', models.IntegerField(default=5000, help_text='max cpu load')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='ClusterGroup',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('name', models.CharField(help_text='Cluster name', max_length=100, unique=True)),
                ('description', models.CharField(help_text='Cluster description', max_length=255, null=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Node',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('slug', models.CharField(help_text='hostname', max_length=100)),
                ('domain', models.CharField(default='bbbconf.de', help_text='Node domain', max_length=50)),
                ('secret', models.CharField(help_text='BBB API secret', max_length=50)),
                ('attendees', models.IntegerField(default=0, help_text='polled number of attendees')),
                ('meetings', models.IntegerField(default=0, help_text='polled number of meetings')),
                ('cpu_load', models.IntegerField(default=0, help_text='cpu load as percentage * 100')),
                ('has_errors', models.BooleanField(default=True, help_text='polling has returned an error')),
                ('maintenance', models.BooleanField(default=False, help_text='node is in maintenance')),
                ('cluster', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='rest.cluster')),
            ],
            options={
                'ordering': ['slug'],
            },
        ),
        migrations.CreateModel(
            name='Secret',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('description', models.CharField(blank=True, default='', max_length=256)),
                ('sub_id', models.SmallIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(999)])),
                ('secret', models.CharField(default=rest.models.get_random_secret, max_length=42, validators=[django.core.validators.RegexValidator('^[a-zA-Z0-9]{42}$')])),
                ('secret2', models.CharField(blank=True, default='', max_length=42, validators=[django.core.validators.RegexValidator('^($|[a-zA-Z0-9]{42})$')])),
            ],
            options={
                'ordering': ['tenant__slug', 'sub_id'],
            },
        ),
        migrations.CreateModel(
            name='Slide',
            fields=[
                ('name', models.CharField(max_length=256, primary_key=True, serialize=False)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='NodeMeetingList',
            fields=[
                ('node', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='rest.node')),
                ('xml', models.TextField(default='')),
            ],
        ),
        migrations.CreateModel(
            name='SecretMeetingList',
            fields=[
                ('secret', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='rest.secret')),
                ('xml', models.TextField(default='')),
            ],
        ),
        migrations.CreateModel(
            name='Tenant',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('slug', models.CharField(max_length=10, validators=[django.core.validators.RegexValidator('[A-Z]{2,10}')])),
                ('description', models.CharField(blank=True, default='', max_length=256)),
                ('stats_token', models.UUIDField(default=uuid.uuid4)),
                ('cluster_group', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='rest.clustergroup')),
                ('slide', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='rest.slide')),
            ],
            options={
                'ordering': ['slug'],
            },
        ),
        migrations.CreateModel(
            name='Stats',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('attendees', models.IntegerField(default=0)),
                ('meetings', models.IntegerField(default=0)),
                ('listenerCount', models.IntegerField(default=0)),
                ('voiceParticipantCount', models.IntegerField(default=0)),
                ('moderatorCount', models.IntegerField(default=0)),
                ('videoCount', models.IntegerField(default=0)),
                ('bbb_origin', models.CharField(default='', max_length=255)),
                ('bbb_origin_server_name', models.CharField(default='', max_length=255)),
                ('tenant', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='rest.tenant')),
            ],
            options={
                'ordering': ['tenant'],
            },
        ),
        migrations.CreateModel(
            name='SecretMetricsList',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('metrics', models.TextField(default='')),
                ('secret', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='rest.secret')),
            ],
        ),
        migrations.AddField(
            model_name='secret',
            name='tenant',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='rest.tenant'),
        ),
        migrations.CreateModel(
            name='Metric',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(choices=[('attendees', 'Total number of current attendees'), ('listeners', 'Total number of current listeners'), ('voices', 'Total number of current voice participants'), ('videos', 'Total number of current video participants'), ('meetings', 'Total number of running meetings'), ('attendees_total', 'Number of attendees that have joined'), ('meetings_total', 'Number of meetings that have been created'), ('meeting_duration_seconds_count', 'Total number of meeting durations'), ('meeting_duration_seconds_sum', 'Sum of meeting durations')], max_length=64)),
                ('value', models.BigIntegerField(default=0)),
                ('node', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rest.node')),
                ('secret', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rest.secret')),
            ],
        ),
        migrations.CreateModel(
            name='Meeting',
            fields=[
                ('id', models.CharField(max_length=100, primary_key=True, serialize=False)),
                ('room_name', models.CharField(max_length=500)),
                ('age', models.DateTimeField(default=django.utils.timezone.now)),
                ('attendees', models.SmallIntegerField(default=0)),
                ('listenerCount', models.SmallIntegerField(default=0)),
                ('voiceParticipantCount', models.SmallIntegerField(default=0)),
                ('moderatorCount', models.SmallIntegerField(default=0)),
                ('videoCount', models.SmallIntegerField(default=0)),
                ('bbb_origin', models.CharField(default='', max_length=255)),
                ('bbb_origin_server_name', models.CharField(default='', max_length=255)),
                ('node', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rest.node')),
                ('secret', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rest.secret')),
            ],
            options={
                'ordering': ['secret__tenant', 'age'],
            },
        ),
        migrations.CreateModel(
            name='ClusterGroupRelation',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('cluster', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='rest.cluster')),
                ('cluster_group', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='rest.clustergroup')),
            ],
            options={
                'ordering': ['cluster_group'],
            },
        ),
        migrations.AddConstraint(
            model_name='secret',
            constraint=models.UniqueConstraint(fields=('tenant', 'sub_id'), name='unique_tenant_id_combination'),
        ),
        migrations.AddConstraint(
            model_name='metric',
            constraint=models.UniqueConstraint(fields=('name', 'secret', 'node'), name='unique_metric'),
        ),
    ]
