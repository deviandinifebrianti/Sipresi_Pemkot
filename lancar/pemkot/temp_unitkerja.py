# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class UnitKerja(models.Model):
    id_unit_kerja = models.AutoField(primary_key=True)
    id_radius = models.ForeignKey('RadiusAbsen', models.DO_NOTHING, db_column='id_radius', blank=True, null=True)
    nama_unit_kerja = models.CharField(max_length=255)
    alamat = models.TextField()
    lattitude = models.FloatField()
    longitude = models.FloatField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'unit_kerja'
