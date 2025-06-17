from django.conf.urls import url
from sipreti import views
from django.conf.urls.static import static
from django.conf import settings


urlpatterns = [
    # # url(r'^$', views.index),
    url(r'add_image', views.add_image),
    url(r'edit_image', views.edit_image),
    url(r'hapus_image', views.hapus_image),
    url(r'verify_image', views.verify_image),
    url(r'login/', views.login, name='login'),
    url(r'daftar/', views.daftar, name='daftar'),
    url(r'user_android/', views.register_android_device, name='register_android_device'),
    url(r'log_absensi/', views.log_absensi, name='log_absensi'),
    # url(r'log_absensi/terbaru/(?P<id_pegawai>\d+)/$', views.get_latest_absensi, name='get_latest_absensi'),
    url(r'get_radius/', views.get_radius, name='get_radius'),
    url(r'get_lokasi_unit_kerja/', views.get_lokasi_unit_kerja, name='get_lokasi_unit_kerja'),
    url(r'unit_kerja/', views.unit_kerja_list, name='unit_kerja_list'),
    url(r'unit_kerja/(?P<id_unit_kerja>\d+)/', views.unit_kerja_detail, name='unit_kerja_detail'),
    url(r'jabatan/', views.jabatan_list, name='jabatan_list'),
    url(r'radius_absen/get_detail_json/<int:id>/', views.get_detail_json, name='get_detail_json'),
    url(r'enroll_face/', views.enroll_face, name='enroll_face'),
    # url(r'kompresi/', views.kompresi_handler, name='kompresi_handler'),
    # url(r'^dekompresi/(?P<kompresi_id>\d+)/$', views.get_decompressed_image, name='get_decompressed_image'),
    url(r'upload_encoded_huffman/', views.upload_encoded_huffman_image, name='upload_encoded_huffman'),
    url(r'^dekompresi/(?P<kompresi_id>\d+)/$', views.upload_encoded_huffman_image, name='upload_encoded_huffman_image'),

    # url(r'^compare/(?P<kompresi_id>\d+)/$', views.compare_images, name='compare_images'),
    # url(r'^verifikasi_dari_kompresi/(?P<kompresi_id>\d+)/$', views.verifikasi_dari_kompresi, name='verifikasi_dari_kompresi'),
    # url(r'^uncompress/(?P<kompresi_id>\d+)/$', views.tampilkan_hasil_dekompresi, name='tampilkan_hasil_dekompresi'),
    # url(r'^verify/(?P<kompresi_id>\d+)/$', views.verifikasi_dari_kompresi, name='verifikasi_dari_kompresi'),
    # url(r'^verifikasi/(?P<kompresi_id>\d+)/$', views.halaman_verifikasi, name='halaman_verifikasi'),
    # url(r'^verifikasi/', views.halaman_verifikasi, name='halaman_verifikasi_all'),
    
    url(r'^process_face/', views.process_face_view, name='process_face'),
    url(r'^rle_decode_image', views.rle_decode_image, name='rle_decode_image'),
    url(r'^encode_image/', views.encode_image, name='encode_image'), #arithmatic
    url(r'^decode_image/', views.decode_image, name='decode_image'),
    
    # kompresi rle
    url(r'kompresi_rle/', views.kompresi_rle, name='kompresi_rle'),


    url(r'upload_profile_photo/', views.upload_profile_photo, name='upload_profile_photo'),
    url(r'get_profile_photo/(?P<id_pegawai>\d+)/$', views.get_profile_photo, name='get_profile_photo'),
    url(r'delete_profile_photo/(?P<id_pegawai>\d+)/$', views.delete_profile_photo, name='delete_profile_photo'),
    url(r'pegawai/(?P<id_pegawai>\d+)/$', views.update_pegawai, name='update_pegawai'),
    url(r'get_attendance/(?P<id_pegawai>\d+)/$', views.get_attendance, name='get_attendance'),
    

    url(r'timing/', views.save_timing_to_db, name='save_timing_to_db'),
    url(r'start/', views.get_timing_stats, name='get_timing_stats'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


