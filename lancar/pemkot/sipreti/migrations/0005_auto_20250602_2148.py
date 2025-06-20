# Generated by Django 3.2.25 on 2025-06-02 14:48

from django.db import migrations, models
import django.db.models.deletion
import sipreti.models


class Migration(migrations.Migration):

    dependencies = [
        ('sipreti', '0004_auto_20250508_2215'),
    ]

    operations = [
        migrations.CreateModel(
            name='KompresiRle',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('id_pegawai', models.CharField(max_length=100)),
                ('width', models.IntegerField()),
                ('height', models.IntegerField()),
                ('original_length', models.IntegerField()),
                ('compressed_size', models.IntegerField()),
                ('original_size', models.IntegerField()),
                ('compression_ratio', models.FloatField()),
                ('compression_time_ms', models.IntegerField()),
                ('compression_type', models.CharField(default='rle', max_length=20)),
                ('compressed_file', models.FileField(upload_to='compressed_files/')),
                ('frequency_model', models.JSONField(blank=True, null=True)),
                ('code_table', models.JSONField(blank=True, null=True)),
                ('is_rgb', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='TimingLog',
            fields=[
                ('id_timing', models.AutoField(primary_key=True, serialize=False)),
                ('id_pegawai', models.CharField(db_index=True, max_length=100)),
                ('server_decode', models.FloatField(blank=True, null=True)),
                ('mobile_capture', models.IntegerField(blank=True, null=True)),
                ('mobile_huffman', models.IntegerField(blank=True, null=True)),
                ('mobile_sending', models.IntegerField(blank=True, null=True)),
                ('mobile_total', models.IntegerField(blank=True, null=True)),
                ('server_add_face', models.IntegerField(blank=True, null=True)),
                ('server_verify', models.IntegerField(blank=True, null=True)),
                ('server_total', models.IntegerField(blank=True, null=True)),
                ('euclidean_distance', models.FloatField(blank=True, null=True)),
                ('verification_success', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name_plural': 'Biometrik',
            },
        ),
        migrations.DeleteModel(
            name='BiometrikPegawaiGroup',
        ),
        migrations.AlterModelOptions(
            name='biometrik',
            options={},
        ),
        migrations.AddField(
            model_name='biometrik',
            name='face_features',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='biometrik',
            name='face_vector',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='biometrik',
            name='hasil_uncompress',
            field=models.ImageField(blank=True, null=True, upload_to=sipreti.models.uncompress_upload_path),
        ),
        migrations.AddField(
            model_name='biometrik',
            name='huffman_codes_path',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='biometrik',
            name='kompresi_id',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='kompresihuffman',
            name='face_vector',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='kompresihuffman',
            name='hasil_uncompress',
            field=models.ImageField(blank=True, null=True, upload_to=sipreti.models.huffman_upload_path),
        ),
        migrations.AddField(
            model_name='kompresihuffman',
            name='huffman_tree',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='kompresihuffman',
            name='tree_depth',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='kompresihuffman',
            name='unique_characters',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='userandroid',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='kompresiarithmetic',
            name='code_table',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='kompresihuffman',
            name='code_table',
            field=models.JSONField(),
        ),
        migrations.AlterField(
            model_name='kompresihuffman',
            name='frequency_model',
            field=models.JSONField(),
        ),
        migrations.AlterField(
            model_name='kompresihuffman',
            name='original_length',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='userandroid',
            name='device_brand',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='userandroid',
            name='device_model',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='userandroid',
            name='device_sdk_version',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='userandroid',
            name='id_pegawai',
            field=models.ForeignKey(db_column='id_pegawai', on_delete=django.db.models.deletion.CASCADE, to='sipreti.pegawai'),
        ),
        migrations.AlterField(
            model_name='userandroid',
            name='last_login',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='userandroid',
            name='username',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterUniqueTogether(
            name='userandroid',
            unique_together=set(),
        ),
    ]
