from django.shortcuts import render
from django.http import JsonResponse, HttpResponseServerError
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.forms.models import model_to_dict
import os
from django.core.files import File
from django.conf import settings
from .models import Biometrik, Jabatan, UnitKerja, RadiusAbsen, Pegawai, LogAbsensi, LogVerifikasi, KompresiRLE, UserAndroid, KompresiHuffman, KompresiArithmetic
from sipreti.face_recognition import main
from django.conf import settings
import time
from .face_recognition.main import add_face
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from rest_framework.decorators import api_view, parser_classes
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.models import User
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import BiometrikSerializer, JabatanSerializer, PegawaiSerializer, LogAbsensiSerializer, RadiusAbsenSerializer, UnitKerjaSerializer
from rest_framework import viewsets
from .models import Pegawai, LogAbsensi
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.contrib.auth.hashers import check_password
import requests
import base64
from PIL import Image
import numpy as np
from io import BytesIO
from .face_recognition.main import add_face
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from collections import Counter
import traceback
import sys
import io
import json
import logging
from django.views.decorators.http import require_http_methods
from django.views.decorators.http import require_GET, require_POST
from django.shortcuts import render, get_object_or_404
import os
import json
import base64
import pickle
from datetime import datetime
import traceback
from django.db import connection
import gzip
import base64
import json
import cv2  # Pastikan opencv-python sudah diinstal

from django.http import JsonResponse, HttpResponseBadRequest
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

path_dataset = settings.MEDIA_ROOT+"/sipreti/dataset/"


# kode decode arithmatic
class ArithmeticCoder:
    def __init__(self):
        self.precision = 32  # 32-bit precision
        self.max_val = (1 << self.precision) - 1
        self.quarter = 1 << (self.precision - 2)
        self.half = 2 * self.quarter
        self.three_quarter = 3 * self.quarter
    
    def build_frequency_model(self, data):
        """Build frequency model from data"""
        counter = Counter(data)
        # Ensure all symbols have at least frequency 1
        for symbol in range(256):  # For 8-bit values
            if symbol not in counter:
                counter[symbol] = 1
        return dict(counter)
    
    def build_cumulative_freq(self, freq_model):
        """Build cumulative frequency table"""
        symbols = sorted(freq_model.keys())
        cumulative = {}
        total = 0
        
        for symbol in symbols:
            cumulative[symbol] = total
            total += freq_model[symbol]
        
        return cumulative, total
    
    def encode(self, data):
        """Encode data using arithmetic coding"""
        if not data:
            return b'', {}
        
        # Build frequency model
        freq_model = self.build_frequency_model(data)
        cumulative, total_freq = self.build_cumulative_freq(freq_model)
        
        # Initialize encoding variables
        low = 0
        high = self.max_val
        pending_bits = 0
        output_bits = []
        
        # Encode each symbol
        for symbol in data:
            # Calculate range
            range_size = high - low + 1
            
            # Update high and low
            symbol_freq = freq_model[symbol]
            symbol_cum = cumulative[symbol]
            
            high = low + (range_size * (symbol_cum + symbol_freq)) // total_freq - 1
            low = low + (range_size * symbol_cum) // total_freq
            
            # Output bits and renormalize
            while True:
                if high < self.half:
                    # Output 0
                    output_bits.append(0)
                    for _ in range(pending_bits):
                        output_bits.append(1)
                    pending_bits = 0
                elif low >= self.half:
                    # Output 1
                    output_bits.append(1)
                    for _ in range(pending_bits):
                        output_bits.append(0)
                    pending_bits = 0
                    low -= self.half
                    high -= self.half
                elif low >= self.quarter and high < self.three_quarter:
                    # Pending bit
                    pending_bits += 1
                    low -= self.quarter
                    high -= self.quarter
                else:
                    break
                
                # Scale up
                low = (low << 1) & self.max_val
                high = ((high << 1) | 1) & self.max_val
        
        # Output final bits
        pending_bits += 1
        if low < self.quarter:
            output_bits.append(0)
            for _ in range(pending_bits):
                output_bits.append(1)
        else:
            output_bits.append(1)
            for _ in range(pending_bits):
                output_bits.append(0)
        
        # Convert bits to bytes
        # Pad to make multiple of 8
        while len(output_bits) % 8 != 0:
            output_bits.append(0)
        
        output_bytes = bytearray()
        for i in range(0, len(output_bits), 8):
            byte = 0
            for j in range(8):
                if i + j < len(output_bits):
                    byte = (byte << 1) | output_bits[i + j]
                else:
                    byte = byte << 1
            output_bytes.append(byte)
        
        return bytes(output_bytes), freq_model
    
    def decode(self, encoded_bytes, freq_model, length):
        """Decode arithmetic coded data"""
        if not encoded_bytes or length == 0:
            return []
        
        # Build cumulative frequency table
        cumulative, total_freq = self.build_cumulative_freq(freq_model)
        symbols = sorted(freq_model.keys())
        
        # Convert bytes to code value
        code = 0
        for byte in encoded_bytes[:4]:  # Use first 4 bytes for initial code
            code = (code << 8) | byte
        
        # Initialize decoding variables
        low = 0
        high = self.max_val
        decoded_data = []
        byte_index = 0
        bit_buffer = 0
        bits_in_buffer = 0
        
        def get_next_bit():
            nonlocal byte_index, bit_buffer, bits_in_buffer
            if bits_in_buffer == 0:
                if byte_index < len(encoded_bytes):
                    bit_buffer = encoded_bytes[byte_index]
                    byte_index += 1
                    bits_in_buffer = 8
                else:
                    return 0  # No more bits
            
            bit = (bit_buffer >> (bits_in_buffer - 1)) & 1
            bits_in_buffer -= 1
            return bit
        
        # Skip initial bits used for code
        for _ in range(32):
            get_next_bit()
        
        # Decode symbols
        for _ in range(length):
            # Find symbol
            range_size = high - low + 1
            scaled_value = ((code - low + 1) * total_freq - 1) // range_size
            
            # Find the symbol that contains scaled_value
            symbol = symbols[0]  # default
            for s in symbols:
                symbol_low = cumulative[s]
                symbol_high = symbol_low + freq_model[s] - 1
                
                if symbol_low <= scaled_value <= symbol_high:
                    symbol = s
                    break
            
            decoded_data.append(symbol)
            
            # Update range
            symbol_cum = cumulative[symbol]
            symbol_freq = freq_model[symbol]
            
            high = low + (range_size * (symbol_cum + symbol_freq)) // total_freq - 1
            low = low + (range_size * symbol_cum) // total_freq
            
            # Renormalize
            while True:
                if high < self.half:
                    pass
                elif low >= self.half:
                    code -= self.half
                    low -= self.half
                    high -= self.half
                elif low >= self.quarter and high < self.three_quarter:
                    code -= self.quarter
                    low -= self.quarter
                    high -= self.quarter
                else:
                    break
                
                low = (low << 1) & self.max_val
                high = ((high << 1) | 1) & self.max_val
                code = ((code << 1) | get_next_bit()) & self.max_val
        
        return decoded_data
    
@csrf_exempt
def decode_image(request):
    """Decode image using arithmetic coding"""
    import time  # ✅ TAMBAH untuk timing
    decode_start_time = time.time()  # ✅ TAMBAH timer

    if request.method != 'POST':
        return HttpResponseBadRequest("Only POST allowed")

    try:
        data = json.loads(request.body.decode('utf-8'))
        encoded_data = data.get('encoded_data')
        model = data.get('model')
        shape = data.get('shape')
        mode = data.get('mode', 'RGB')

        if not (encoded_data and model and shape):
            return JsonResponse({"error": "Missing required data"}, status=400)

        id_pegawai = data.get('id_pegawai')
        if not id_pegawai:
            return JsonResponse({"error": "Missing id_pegawai"}, status=400)
        
        # ✅ TAMBAH: Hitung ukuran compressed data
        compressed_size = len(encoded_data) if encoded_data else 0
        decompression_start = time.time()
        
        # Convert model keys from string to int (JSON converts int keys to strings)
        freq_model = {int(k): v for k, v in model.items()}

        # Decode base64 to bytes
        bitstream = base64.b64decode(encoded_data)

        # Decode using arithmetic coding
        coder = ArithmeticCoder()
        decoded_pixels = coder.decode(bitstream, freq_model, np.prod(shape))

        decompression_time = time.time() - decompression_start

         # ✅ TAMBAH: Hitung ukuran decoded
        if len(shape) == 3:  # RGB
            decoded_size = shape[0] * shape[1] * shape[2]
        else:  # Grayscale
            decoded_size = shape[0] * shape[1]

        # Reconstruct image array
        image_array = np.array(decoded_pixels, dtype=np.uint8).reshape(shape)

        # Create PIL Image
        if len(shape) == 3 and shape[2] == 3:
            pil_image = Image.fromarray(image_array, mode='RGB')
        elif len(shape) == 2:
            pil_image = Image.fromarray(image_array, mode='L')
        else:
            pil_image = Image.fromarray(image_array, mode='RGB')

        # Siapkan direktori penyimpanan
        output_dir = os.path.join(settings.MEDIA_ROOT, "arithmatic_images", str(id_pegawai))
        os.makedirs(output_dir, exist_ok=True)

        # Buat nama file berdasarkan waktu dan mode
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_arithmatic.jpg"
        save_path = os.path.join(output_dir, filename)
        
        pil_image.save(save_path, 'JPEG')
        image_url = f"{settings.MEDIA_URL}arithmatic_images/{id_pegawai}/{filename}"

        total_decode_time = time.time() - decode_start_time

        # ✅ TAMBAH: Auto create face vector
        print(f"🤖 Auto creating face vector for arithmetic...")
        mobile_timing = data.get('mobile_timing')  # Ambil timing dari mobile jika ada
        
        try:
            face_vector_result = face_vector_arithmetic(id_pegawai, save_path, mobile_timing)
            print(f"✅ Face vector result: {face_vector_result}")
        except Exception as face_error:
            print(f"❌ Face vector creation failed: {face_error}")
            import traceback
            traceback.print_exc()
            face_vector_result = {"success": False, "message": f"Face vector error: {str(face_error)}"}
        
        # ✅ TAMBAH: Hitung total decode time

        response_data = {
            "status": "success",
            "decoded_shape": list(image_array.shape),
            "image_saved": True,
            "image_url": image_url,
            "filename": filename,
            "save_path": save_path,
            "decoded_pixels": len(decoded_pixels),
            "pixel_stats": {
                "min": int(np.min(image_array)),
                "max": int(np.max(image_array)),
                "mean": float(np.mean(image_array))
            }, 
            #  ✅ Data statistik untuk mobile (sama format dengan RLE/Huffman)
            'compressed_size': compressed_size,
            'decoded_size': decoded_size,
            'decompression_time_seconds': decompression_time,
            'total_decode_time_seconds': total_decode_time,
            
            # ✅ Face vector result
            'face_vector_result': face_vector_result
        }
        return JsonResponse(response_data)
        
    except Exception as e:
        import traceback
        traceback.print_exc() 
        return JsonResponse({"error": str(e)}, status=500)
        
# ✅ 2. Function face_vector_arithmetic
def face_vector_arithmetic(id_pegawai, latest_image_path=None, mobile_timing=None):
    """
    Function untuk auto-create face vector untuk Arithmetic Coding
    """
    import time
    start_time = time.time()

    try:
        import os
        import json
        from django.conf import settings
        from sipreti.face_recognition.main import add_face_local
        
        # Cari folder gambar arithmetic
        arithmetic_folder = os.path.join(settings.MEDIA_ROOT, 'arithmatic_images', str(id_pegawai))
        
        if not os.path.exists(arithmetic_folder):
            return {"success": False, "message": "Folder tidak ditemukan"}
        
        # Kumpulkan gambar - PRIORITASKAN GAMBAR TERBARU
        image_paths = []
        if latest_image_path and os.path.exists(latest_image_path):
            image_paths = [latest_image_path]
            
        else:
            # Ambil semua gambar dan urutkan berdasarkan waktu
            all_images = []
            for filename in os.listdir(arithmetic_folder):
                if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                    image_path = os.path.join(arithmetic_folder, filename)
                    mtime = os.path.getmtime(image_path)
                    all_images.append((mtime, image_path, filename))
            
            # Urutkan berdasarkan waktu terbaru
            all_images.sort(reverse=True)
            
            # Ambil maksimal 3 gambar terbaru untuk efisiensi
            image_paths = [img[1] for img in all_images[:3]]
            
            for _, _, filename in all_images[:3]:
                print(f"Found arithmetic image: {filename}")
        
        if not image_paths:
            return {"success": False, "message": "Tidak ada gambar arithmetic"}
        
        # Buat face vector
        add_face_start = time.time()
        
        try:
            face_vector_data = add_face_local(image_paths)
            add_face_time = time.time() - add_face_start
            
            # Cek hasil face vector
            print(f"🔍 Received from add_face_local:")
            print(f"   Type: {type(face_vector_data)}")
            print(f"   Value: {face_vector_data}")
            print(f"   Is not False: {face_vector_data is not False}")
            print(f"   Is not None: {face_vector_data is not None}")
            
        except Exception as face_extract_error:
            print(f"❌ Error extracting face features: {face_extract_error}")
            import traceback
            traceback.print_exc()
            return {"success": False, "message": f"Face extraction error: {str(face_extract_error)}"}
        
        # Kondisi untuk mengecek face_vector_data
        if (face_vector_data is not None and 
            face_vector_data is not False and 
            len(face_vector_data) > 0):
    
            db_save_start = time.time()
            
            # Simpan ke database - Buat table baru untuk Arithmetic
            from .models import KompresiArithmetic  # ✅ PERLU BUAT MODEL BARU
            from django.utils import timezone

            record = KompresiArithmetic.objects.create(
                id_pegawai=str(id_pegawai),   
                width=0,
                height=0,
                frequency_model="{}",
                encoded_data="",
                face_vector=json.dumps(face_vector_data),
                created_at=timezone.now()
            ) 
            db_save_time = time.time() - db_save_start

            # Hitung total untuk user
            total_count = KompresiArithmetic.objects.filter(
                id_pegawai=str(id_pegawai))

            verify_start = time.time()
            # Panggil function verify dengan error handling
            try:
                verify_result = auto_verify_after_enrollment_arithmetic(record.id, str(id_pegawai), image_paths[0])
                verify_time = time.time() - verify_start
                verification_status = "✅ VERIFIED" if verify_result else "❌ FAILED"
                                    
            except Exception as verify_error:
                print(f"❌ Verification error: {verify_error}")
                import traceback
                traceback.print_exc()
                verify_result = False
                verify_time = time.time() - verify_start
                verification_status = "❌ VERIFICATION ERROR"

                total_face_time = time.time() - start_time
                
                # Buat timing summary
                server_timing = {
                    'add_face_ms': round(add_face_time * 1000),
                    'db_save_ms': round(db_save_time * 1000),
                    'verify_ms': round(verify_time * 1000),
                    'total_face_ms': round(total_face_time * 1000)
                }
                
            # Simpan timing log
            if mobile_timing:
                try:
                    save_timing_to_db_arithmetic(id_pegawai, mobile_timing, server_timing, verify_result)
                except Exception as e:
                    print(f"⚠️ Failed to save arithmetic timing log: {e}")

            return {
                "success": True, 
                "message": f"Arithmetic face vector saved! {verification_status}", 
                "auto_verification": verify_result,
                "timing": {
                    "mobile": mobile_timing,
                    "server": server_timing
                },
                "kompresi_id": record.id
            }
        else:
            total_time = time.time() - start_time
            print(f"❌ Arithmetic face vector creation failed after {total_time:.3f}s")
            return {"success": False, "message": "Failed to create arithmetic face vector"}
                  
    except Exception as e:
        import traceback
        print(f"❌ Arithmetic face vector error: {str(e)}")
        traceback.print_exc()
        return {"success": False, "message": str(e)}


# ✅ 3. Auto verify setelah enrollment untuk Arithmetic
def auto_verify_after_enrollment_arithmetic(record_id, id_pegawai, image_path):
    """
    Function untuk verify setelah enrollment arithmetic
    """
    try:
        
        # Pastikan file gambar ada
        if not os.path.exists(image_path):
            print(f"❌ Image file not found: {image_path}")
            return False
        
        # Import yang diperlukan
        import sipreti.face_recognition.main as main
        from django.conf import settings
        
        # Buat URL relatif dari image path
        try:
            relative_path = os.path.relpath(image_path, settings.MEDIA_ROOT)
            image_url = f"http://localhost:8000{settings.MEDIA_URL}{relative_path.replace(os.sep, '/')}"
            
        except Exception as url_error:
            print(f"❌ Error generating image URL: {url_error}")
            return False
       
        # Panggil verify_face_arithmetic dengan error handling
        try:
            verify_result = main.verify_face_arithmetic(image_url, str(id_pegawai))
            return verify_result
            
        except Exception as verify_error:
            print(f"❌ Verify face arithmetic error: {verify_error}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"❌ Auto verify arithmetic error: {e}")
        import traceback
        traceback.print_exc()
        return False

    
# ✅ 6. Function untuk save timing log arithmetic
# def save_timing_to_db_arithmetic(id_pegawai, mobile_timing, server_timing, verify_result):
#     """
#     Simpan timing log ke database untuk arithmetic
#     """
#     try:
#         # Implementasi sesuai kebutuhan - contoh:
#         print(f"📊 Timing log for {id_pegawai}:")
#         print(f"   Mobile: {mobile_timing}")  
#         print(f"   Server: {server_timing}")
#         print(f"   Verify: {verify_result}")
        
#         # Bisa simpan ke table TimingLogArithmetic jika diperlukan
#         pass
        
#     except Exception as e:
#         print(f"❌ Save timing arithmetic error: {e}")

@csrf_exempt
def add_image(request):
    import json
    
    time.sleep(3)
    if request.method == 'POST':
        id_pegawai = request.POST['id_pegawai']
        name = request.POST['name']
        image_file = request.FILES.get('image')

        if not image_file:
            return HttpResponseServerError("Memerlukan File Gambar")

        # Simpan file ke folder media/biometrik/<id_pegawai>/
        folder_path = os.path.join('biometrik', str(id_pegawai))
        file_name = f"{int(time.time())}_{image_file.name}"
        saved_path = default_storage.save(os.path.join(folder_path, file_name), ContentFile(image_file.read()))
        image_url = request.build_absolute_uri(os.path.join(settings.MEDIA_URL, saved_path))

        biometrik = Biometrik.objects.filter(id_pegawai=id_pegawai)

        if biometrik.count() == 0:
            # Jika belum ada data biometrik untuk pegawai ini
            url_image_array = [image_url]
        else:
            # Jika sudah ada, gabungkan dengan gambar yang sudah ada
            url_image_array = [b.image for b in biometrik]
            url_image_array.append(image_url)

        # PERBAIKAN: Panggil add_face dengan 1 parameter saja
        face_vector = main.add_face(url_image_array)

        if face_vector:  # Jika berhasil extract face vector
            # Simpan ke database
            face_id = insert_image_db(id_pegawai, name, image_url, face_vector)
            
            # Hapus gambar duplikat
            seen = set()
            for row in Biometrik.objects.all():
                if row.image in seen:
                    row.delete()
                else:
                    seen.add(row.image)
                    
            response = {'status': 1, 'message': "Berhasil", "face_id": face_id}
        else:
            # Jika gagal extract face vector
            if biometrik.count() > 0:
                # Jika sudah ada data sebelumnya, coba proses ulang tanpa gambar baru
                url_image_array_fallback = [b.image for b in biometrik]
                fallback_vector = main.add_face(url_image_array_fallback)
                
                if fallback_vector:
                    # Update dengan face vector dari gambar lama
                    face_vector_json = json.dumps(fallback_vector)
                    Biometrik.objects.filter(id_pegawai=id_pegawai).update(
                        face_vector=face_vector_json
                    )
                    
            # Tetap simpan gambar tapi tanpa face vector
            face_id = insert_image_db(id_pegawai, name, image_url, None)
            response = {'status': 0, 'message': "Gagal extract face vector", "face_id": face_id}

        print(response)
        return JsonResponse(response)

def insert_image_db(id_pegawai, name, url_image, face_vector=None):
    from .models import Biometrik, Pegawai
    import json
    
    # Konversi face_vector ke JSON string jika ada
    face_vector_json = json.dumps(face_vector) if face_vector else ''
    
    try:
        # Ambil instance Pegawai dari id
        pegawai = Pegawai.objects.get(id_pegawai=id_pegawai)
    except Pegawai.DoesNotExist:
        return None

    # Insert image dengan face_vector
    insert_biometrik = Biometrik.objects.create(
        id_pegawai=pegawai,
        name=name,
        image=url_image,
        face_vector=face_vector_json  # Simpan face vector di sini
    )
    insert_biometrik.save()
    
    id_biometrik = insert_biometrik.id
    face_id = str(id_pegawai) + "." + str(id_biometrik)
    
    # Update dengan face_id
    Biometrik.objects.filter(id=id_biometrik).update(
        face_id=face_id
    )
    
    return face_id

# simpan vector ke tabel pegawai (ini dari mobile)
def upload_and_process_photo(request):
    import json
    import os
    
    if request.method == 'POST':
        id_pegawai = request.POST.get('id_pegawai')
        name = request.POST.get('name', '')
        image_file = request.FILES.get('image')

        if not image_file or not id_pegawai:
            return JsonResponse({
                'status': 0, 
                'message': "ID Pegawai dan file gambar diperlukan"
            })

        try:
            # 1. SIMPAN FILE
            folder_path = os.path.join('huffman_images_vector', str(id_pegawai))
            file_name = f"{int(time.time())}_{image_file.name}"
            saved_path = default_storage.save(
                os.path.join(folder_path, file_name), 
                ContentFile(image_file.read())
            )
            
            # 2. CONVERT KE ABSOLUTE PATH
            absolute_path = os.path.join(settings.MEDIA_ROOT, saved_path)

            # 3. KUMPULKAN SEMUA PATH FOTO PEGAWAI INI
            image_paths_list = [absolute_path]
            
            # Cari foto lama jika ada
            try:
                pegawai = Pegawai.objects.get(id_pegawai=id_pegawai)
                if pegawai.foto:
                    old_absolute_path = os.path.join(settings.MEDIA_ROOT, str(pegawai.foto))
                    if os.path.exists(old_absolute_path) and old_absolute_path != absolute_path:
                        image_paths_list.insert(0, old_absolute_path)
            except Pegawai.DoesNotExist:
                pass

            # 4. EXTRACT FACE VECTOR LANGSUNG
            face_vector = main.add_face_from_local_path(image_paths_list)
            
            if face_vector:
                # 5. SIMPAN KE TABEL PEGAWAI KOLOM FACE_VECTOR
                face_vector_json = json.dumps(face_vector)
                
                try:
                    # Update pegawai yang sudah ada
                    pegawai = Pegawai.objects.get(id_pegawai=id_pegawai)
                    pegawai.foto = saved_path
                    pegawai.face_vector = face_vector_json  # SIMPAN DI KOLOM FACE_VECTOR
                    if name:
                        pegawai.name = name
                    pegawai.save()
  
                except Pegawai.DoesNotExist:
                    # Buat pegawai baru
                    pegawai = Pegawai.objects.create(
                        id_pegawai=id_pegawai,
                        name=name,
                        foto=saved_path,
                        face_vector=face_vector_json  # SIMPAN DI KOLOM FACE_VECTOR
                    )
 
                response = {
                    'status': 1,
                    'message': 'Foto berhasil diupload dan face vector tersimpan di database!',
                    'filename': file_name,
                    'vector_length': len(face_vector),
                    'id_pegawai': id_pegawai,
                    'saved_to': 'tabel_pegawai.face_vector'
                }
                
            else:
                # Gagal extract face vector, tetap simpan foto tanpa face_vector
                try:
                    pegawai = Pegawai.objects.get(id_pegawai=id_pegawai)
                    pegawai.foto = saved_path
                    if name:
                        pegawai.name = name
                    pegawai.save()
                except Pegawai.DoesNotExist:
                    pegawai = Pegawai.objects.create(
                        id_pegawai=id_pegawai,
                        name=name,
                        foto=saved_path,
                        face_vector=None  # NULL karena gagal extract
                    )
                
                response = {
                    'status': 0,
                    'message': 'Foto tersimpan tapi gagal extract face vector',
                    'filename': file_name,
                    'id_pegawai': id_pegawai,
                    'face_detected': False
                }

            return JsonResponse(response)
            
        except Exception as e:
            print(f"🚨 Error: {str(e)}")
            return JsonResponse({
                'status': 0,
                'message': f'Error processing: {str(e)}'
            })

@csrf_exempt
def edit_image(request):
    time.sleep(3)
    face_id = request.POST['face_id']
    url_image = request.POST['url_image']
    name = request.POST['name']

    biometrik = Biometrik.objects.filter(face_id=face_id)
    if(biometrik.count()==0):
        response = {'status':2,'message':"Gagal. Data Face_id Tidak Ditemukan."}
    else:
        id_pegawai = str(biometrik[0].id_pegawai)
        file_name = str(id_pegawai)
        biometrik_new = Biometrik.objects.filter(id_pegawai=id_pegawai).exclude(face_id=face_id)
        url_image_array = []
        if(biometrik_new.count()>0):
            for data_bio in biometrik_new:
                url_image_array.append(data_bio.image)
            url_image_array.append(url_image)
        else:
           url_image_array.append(url_image) 
        adding_face = main.add_face(url_image_array,file_name)

        if(adding_face==False):
            url_image_array = []
            biometrik_new2 = Biometrik.objects.filter(id_pegawai=id_pegawai)
    
            if(biometrik_new2.count()>0):
                for data_bio in biometrik_new2:
                    url_image_array.append(data_bio.image)
                # print(url_image_array)
                main.add_face(url_image_array,file_name)

        if(adding_face):
            face_id = update_image_db(face_id,name,url_image)
            response = {'status':1,'message':"Berhasil","face_id":face_id}
        else:
            response = {'status':0,'message':"Gagal"}
    print(response)
    return JsonResponse(response) 

def update_image_db(face_id,name,url_image):
    biometrik = Biometrik.objects.filter(face_id=face_id)
    biometrik.update(name=name,image=url_image)
    return biometrik[0].face_id

@csrf_exempt
def hapus_image(request):
    time.sleep(3)
    face_id = request.POST['face_id']
    biometrik = Biometrik.objects.filter(face_id=face_id)
    if(biometrik.count()>0):
        id_pegawai = str(biometrik[0].id_pegawai)

        # hapus db
        delete = biometrik.delete()

        # cek biometrik ada berapa
        biometrik_new = Biometrik.objects.filter(id_pegawai=id_pegawai)
        if(biometrik_new.count()==0):
            if(os.path.exists(path_dataset+id_pegawai+'.txt')):
                os.remove(path_dataset+id_pegawai+'.txt')
        else:
            url_image_array = []
            for data_bio in biometrik_new:
                url_image_array.append(data_bio.image)
            file_name = str(id_pegawai)
            adding_face = main.add_face(url_image_array,file_name)

        if(delete):
            response = {'status':1,'message':"Berhasil."}
        else:
            response = {'status':0,'message':"Gagal."}
    else:
        response = {'status':0,'message':"Gagal. face_id tidak ditemukan"}
    print(response)
    return JsonResponse(response) 

@csrf_exempt
def verify_image(request):
    if request.method != 'POST':
        return HttpResponseServerError("Invalid request method")

    id_pegawai = request.POST.get('id_pegawai')
    image_file = request.FILES.get('image')

    if not id_pegawai or not image_file:
        return HttpResponseServerError("Missing id_pegawai or image file")

    biometrik = Biometrik.objects.filter(id_pegawai=id_pegawai)

    if not biometrik.exists():
        return JsonResponse({'status': 0, 'message': "Id Pegawai Tidak ditemukan."})

    # Simpan gambar ke folder verification/<id_pegawai>/
    folder_path = os.path.join('verification', str(id_pegawai))
    file_name = f"{int(time.time())}_{image_file.name}"
    saved_path = default_storage.save(os.path.join(folder_path, file_name), ContentFile(image_file.read()))
    image_url = request.build_absolute_uri(os.path.join(settings.MEDIA_URL, saved_path))

    try:
        # Gunakan image_path sebagai input ke verify_face
        cek_image = main.verify_face(image_url, id_pegawai)

        if cek_image:
            response = {'status': 1, 'message': "Cocok."}
        else:
            response = {'status': 0, 'message': "Tidak Cocok."}

    finally:
        # Hapus gambar setelah proses selesai
        if os.path.exists(image_url):
            os.remove(image_url)

    print(response)
    return JsonResponse(response)

@csrf_exempt
def upload_profile_photo(request):
    if request.method == 'POST':
        try:
            id_pegawai = request.POST.get('id_pegawai')
            profile_image = request.FILES.get('profile_image')
            
            if not id_pegawai or not profile_image:
                return JsonResponse({
                    'status': 'error',
                    'message': 'id_pegawai dan profile_image harus diisi'
                }, status=400)
            
            # Validasi file
            allowed_extensions = ['.jpg', '.jpeg', '.png']
            file_extension = os.path.splitext(profile_image.name)[1].lower()
            
            if file_extension not in allowed_extensions:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Format file tidak didukung. Gunakan JPG, JPEG, atau PNG'
                }, status=400)
            
            # Batasi ukuran file (max 5MB)
            if profile_image.size > 5 * 1024 * 1024:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Ukuran file maksimal 5MB'
                }, status=400)
            
            # HAPUS FOTO LAMA TERLEBIH DAHULU
            with connection.cursor() as cursor:
                cursor.execute("SELECT image FROM pegawai WHERE id_pegawai = %s", [id_pegawai])
                result = cursor.fetchone()
                
                if result and result[0]:
                    old_file_path = os.path.join(settings.MEDIA_ROOT, result[0])
                    if os.path.exists(old_file_path):
                        try:
                            os.remove(old_file_path)
                        except Exception as e:
                            print(f"⚠️ Gagal hapus foto lama: {e}")
            
            # Buat nama file unik (REPLACE, bukan tambah)
            timestamp = int(time.time())
            file_name = f"profile_{id_pegawai}_{timestamp}{file_extension}"
            
            # Simpan file ke folder profile
            folder_path = os.path.join('profile', str(id_pegawai))
            file_path = os.path.join(folder_path, file_name)
            
            # Simpan file baru
            saved_path = default_storage.save(file_path, ContentFile(profile_image.read()))
            
            # Update kolom IMAGE di database (REPLACE)
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE pegawai 
                    SET image = %s
                    WHERE id_pegawai = %s
                """, [saved_path, id_pegawai])
                
                # Verifikasi update berhasil
                cursor.execute("SELECT ROW_COUNT()")
                affected_rows = cursor.fetchone()[0]
                
                if affected_rows == 0:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Pegawai tidak ditemukan'
                    }, status=404)
            
            # URL foto untuk response
            photo_url = request.build_absolute_uri(os.path.join(settings.MEDIA_URL, saved_path))
            
            return JsonResponse({
                'status': 'success',
                'message': 'Foto profil berhasil diupdate',
                'data': {
                    'foto_url': photo_url,
                    'file_path': saved_path
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Method tidak diizinkan'
    }, status=405)

@csrf_exempt
def get_profile_photo(request, id_pegawai):
    if request.method == 'GET':
        try:
            with connection.cursor() as cursor:
                # Ambil dari kolom IMAGE yang sudah ada
                cursor.execute("SELECT image FROM pegawai WHERE id_pegawai = %s", [id_pegawai])
                result = cursor.fetchone()
                
                if result and result[0]:
                    # Cek apakah file benar-benar ada
                    file_path = os.path.join(settings.MEDIA_ROOT, result[0])
                    if os.path.exists(file_path):
                        photo_url = request.build_absolute_uri(os.path.join(settings.MEDIA_URL, result[0]))
                        return JsonResponse({
                            'status': 'success',
                            'data': {
                                'foto_url': photo_url,
                                'has_photo': True
                            }
                        })
                    else:
                        # File tidak ada, hapus referensi di database
                        cursor.execute("UPDATE pegawai SET image = NULL WHERE id_pegawai = %s", [id_pegawai])
                        
                return JsonResponse({
                    'status': 'success',
                    'data': {
                        'foto_url': None,
                        'has_photo': False
                    }
                })
                    
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Method tidak diizinkan'
    }, status=405)

@csrf_exempt 
def delete_profile_photo(request, id_pegawai):
    """Endpoint untuk hapus foto profil"""
    if request.method == 'DELETE':
        try:
            with connection.cursor() as cursor:
                # Ambil path foto lama
                cursor.execute("SELECT image FROM pegawai WHERE id_pegawai = %s", [id_pegawai])
                result = cursor.fetchone()
                
                if result and result[0]:
                    # Hapus file fisik
                    old_file_path = os.path.join(settings.MEDIA_ROOT, result[0])
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)
                    
                    # Hapus referensi di database
                    cursor.execute("UPDATE pegawai SET image = NULL WHERE id_pegawai = %s", [id_pegawai])
                    
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Foto profil berhasil dihapus'
                    })
                else:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Foto profil tidak ditemukan'
                    }, status=404)
                    
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Method tidak diizinkan'
    }, status=405)

from sipreti.face_recognition.main import add_face_local

@csrf_exempt
def process_face_view(request):
    """
    View Django untuk membuat vektor wajah dari gambar hasil dekompresi
    dengan fokus pada konversi gambar grayscale menjadi RGB
    """
    if request.method != 'POST':
        return JsonResponse({"success": False, "message": "Hanya metode POST yang diizinkan"}, status=405)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "message": "Format JSON tidak valid"}, status=400)
    
    # Ambil ID pegawai
    id_pegawai = data.get('id_pegawai')
    if not id_pegawai:
        return JsonResponse({"success": False, "message": "ID pegawai diperlukan"}, status=400)
    
    # Path ke folder gambar hasil dekompresi
    huffman_folder = os.path.join(settings.MEDIA_ROOT, 'huffman_images', id_pegawai)
    
    if not os.path.exists(huffman_folder):
        return JsonResponse({
            "success": False, 
            "message": f"Folder {huffman_folder} tidak ditemukan"
        }, status=404)
    
    image_paths = []  # Ganti dari image_urls ke image_paths
    colorized_files = []
    
    # Proses gambar: cek dan konversi ke RGB jika perlu
    for filename in os.listdir(huffman_folder):
        # Hanya proses file gambar asli (bukan hasil konversi sebelumnya)
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')) and not filename.startswith(('rgb_', 'color_')):
            try:
                # Path gambar asli
                image_path = os.path.join(huffman_folder, filename)
                print(f"Memeriksa gambar: {image_path}")
                
                # Baca gambar
                img = cv2.imread(image_path)
                
                if img is None:
                    print(f"Gagal membaca gambar: {image_path}")
                    continue
                
                # Cek apakah gambar adalah grayscale (semua channel RGB sama)
                is_grayscale = True
                # Sampel beberapa piksel untuk efisiensi
                height, width = img.shape[:2]
                num_samples = min(100, height * width)
                
                for _ in range(num_samples):
                    y = np.random.randint(0, height)
                    x = np.random.randint(0, width)
                    pixel = img[y, x]
                    
                    # Jika channel RGB berbeda, gambar berwarna
                    if not (pixel[0] == pixel[1] == pixel[2]):
                        is_grayscale = False
                        break
                
                # Jika gambar grayscale, buat versi RGB dengan warna
                if is_grayscale:
                    print(f"Gambar {filename} terdeteksi sebagai grayscale, mengkonversi ke RGB dengan warna...")
                    
                    # Konversi ke grayscale yang sebenarnya
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    
                    # Tingkatkan kontras
                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                    enhanced_gray = clahe.apply(gray)
                    
                    # 1. Buat versi berwarna dengan colormap
                    colored_img = cv2.applyColorMap(enhanced_gray, cv2.COLORMAP_BONE)
                    color_filename = f"color_{filename}"
                    color_path = os.path.join(huffman_folder, color_filename)
                    cv2.imwrite(color_path, colored_img)
                    print(f"Gambar berwarna (colormap) disimpan di: {color_path}")
                    colorized_files.append(color_filename)
                    
                    # 2. Tambahkan URL gambar berwarna
                    color_path = request.build_absolute_uri(f"{settings.MEDIA_URL}huffman_images/{id_pegawai}/{color_filename}")
                    image_paths.append(color_path)
                
                # Selalu tambahkan URL gambar asli
                original_path = request.build_absolute_uri(f"{settings.MEDIA_URL}huffman_images/{id_pegawai}/{filename}")
                image_path.append(image_path)
                
            except Exception as e:
                print(f"Error memproses gambar {filename}: {str(e)}")
    
    # Tambahkan semua gambar berwarna yang sudah ada sebelumnya
    for filename in os.listdir(huffman_folder):
        if filename.startswith('color_') and filename not in colorized_files:
            color_path = request.build_absolute_uri(f"{settings.MEDIA_URL}huffman_images/{id_pegawai}/{filename}")
            if color_path not in image_path:
                image_path.append(color_path)
    
    if not image_path:
        return JsonResponse({
            "success": False,
            "message": "Tidak ada gambar yang ditemukan"
        }, status=404)

    image_formats = []
    
    for filename in os.listdir(huffman_folder):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            image_path = os.path.join(huffman_folder, filename)
            
            try:
                # Baca gambar
                img = cv2.imread(image_path)
                
                if img is None:
                    print(f"Gagal membaca gambar: {image_path}")
                    continue
                
                # Dapatkan informasi dasar
                height, width = img.shape[:2]
                channels = 1 if len(img.shape) == 2 else img.shape[2]
                
                # Periksa apakah gambar efektif grayscale (semua channel RGB sama)
                is_effectively_grayscale = True
                
                if channels >= 3:
                    # Sampel beberapa piksel
                    num_samples = min(20, height * width)
                    for _ in range(num_samples):
                        y = np.random.randint(0, height)
                        x = np.random.randint(0, width)
                        pixel = img[y, x]
                        if not (pixel[0] == pixel[1] == pixel[2]):
                            is_effectively_grayscale = False
                            break
                
                # Ambil contoh beberapa piksel
                sample_pixels = []
                sample_points = [(0, 0), (width-1, 0), (0, height-1), (width-1, height-1), (width//2, height//2)]
                
                for x, y in sample_points:
                    pixel = img[y, x]
                    if channels >= 3:
                        pixel_info = f"({x},{y}): B={pixel[0]}, G={pixel[1]}, R={pixel[2]}"
                    else:
                        pixel_info = f"({x},{y}): Val={pixel}"
                    sample_pixels.append(pixel_info)
                
                # Tambahkan ke daftar format
                image_formats.append({
                    "filename": filename,
                    "dimensions": f"{width}x{height}",
                    "channels": channels,
                    "format": "RGB" if channels >= 3 else "Grayscale",
                    "is_effectively_grayscale": is_effectively_grayscale,
                    "sample_pixels": sample_pixels[:2]  # batasi output untuk kejelasan
                })
                
            except Exception as e:
                print(f"Error checking image {filename}: {str(e)}")
    
    # Cetak hasil
    print(json.dumps(image_formats, indent=2))
    
    # Hitung statistik
    rgb_count = sum(1 for info in image_formats if info.get("format") == "RGB" and not info.get("is_effectively_grayscale"))
    grayscale_count = sum(1 for info in image_formats if info.get("format") == "Grayscale" or info.get("is_effectively_grayscale"))
    colormap_count = sum(1 for info in image_formats if info.get("filename").startswith("color_"))

    try:
        # UBAH: Gunakan fungsi add_face_local dengan PATH bukan URL
        print(f"🔄 Memproses {len(image_paths)} gambar dengan add_face_local...")
        face_vector = add_face_local(image_paths)  # Panggil function Anda
        
        if face_vector:
            # TAMBAHAN: Simpan ke database tabel pegawai
            import json
            face_vector_json = json.dumps(face_vector)
            
            try:
                # Update pegawai dengan face vector
                from .models import Pegawai  # Sesuaikan import
                
                pegawai, created = Pegawai.objects.get_or_create(
                    id_pegawai=id_pegawai,
                    defaults={'name': f'Pegawai {id_pegawai}'}  # Default name jika belum ada
                )
                
                pegawai.face_vector = face_vector_json
                pegawai.save()
                
                return JsonResponse({
                    "success": True,
                    "message": "Berhasil membuat dan menyimpan vektor wajah ke database!",
                    "id_pegawai": id_pegawai,
                    "vector_length": len(face_vector),
                    "image_count": len(image_paths),
                    "colorized_count": len(colorized_files),
                    "saved_to_database": True
                })
                
            except Exception as db_error:
                print(f"❌ Error simpan ke database: {str(db_error)}")
                
                # Tetap return success karena face vector berhasil dibuat
                return JsonResponse({
                    "success": True,
                    "message": f"Face vector berhasil dibuat tapi gagal simpan ke database: {str(db_error)}",
                    "vector_length": len(face_vector),
                    "image_count": len(image_paths),
                    "saved_to_database": False
                })
        else:
            return JsonResponse({
                "success": False,
                "message": "Gagal membuat vektor wajah dari gambar",
                "image_count": len(image_paths)
            })
            
    except Exception as e:
        print(f"🚨 Error dalam add_face_local: {str(e)}")
        return JsonResponse({
            "success": False,
            "message": f"Error: {str(e)}"
        }, status=500)

# digunakan untuk verifikasi setelah mendapatkan hasil decode
def auto_verify_after_enrollment(record_id, id_pegawai, image_path):
    """
    Function BARU untuk verify setelah enrollment - PANGGIL MAIN
    """
    try:
        print(f"🔄 Auto verify starting for record {record_id}")
        
        # PANGGIL verify_face di main
        import sipreti.face_recognition.main as main
        
        # Buat URL dari image path
        from django.conf import settings
        relative_path = os.path.relpath(image_path, settings.MEDIA_ROOT)
        image_url = f"http://localhost:8000{settings.MEDIA_URL}{relative_path.replace(os.sep, '/')}"
        
        print(f"🔄 Calling main.verify_face...")
        
        # PANGGIL VERIFY_FACE DI MAIN
        verify_result = main.verify_face(image_url, str(id_pegawai))
        
        print(f"📊 Main verify_face result: {verify_result}")
        
        return verify_result
        
    except Exception as e:
        print(f"❌ Auto verify error: {e}")
        return False
    
    
# ini create vektor yang dari mobile
def face_vector(id_pegawai, latest_image_path=None, mobile_timing=None):
    """
    Function simple untuk auto-create face vector - FIXED VERSION
    """
    import time
    start_time = time.time()

    try:
        import os
        import json
        from django.conf import settings
        from sipreti.face_recognition.main import add_face_local
        
        # Cari folder gambar
        huffman_folder = os.path.join(settings.MEDIA_ROOT, 'huffman_images', str(id_pegawai))
        
        if not os.path.exists(huffman_folder):
            return {"success": False, "message": "Folder tidak ditemukan"}
        
        # Kumpulkan gambar - PRIORITASKAN GAMBAR TERBARU
        image_paths = []
        if latest_image_path and os.path.exists(latest_image_path):
            image_paths = [latest_image_path]
        else:
            # Ambil semua gambar dan urutkan berdasarkan waktu
            all_images = []
            for filename in os.listdir(huffman_folder):
                if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                    image_path = os.path.join(huffman_folder, filename)
                    mtime = os.path.getmtime(image_path)
                    all_images.append((mtime, image_path, filename))
            
            # Urutkan berdasarkan waktu terbaru
            all_images.sort(reverse=True)
            
            # Ambil maksimal 3 gambar terbaru untuk efisiensi
            image_paths = [img[1] for img in all_images[:3]]
            
            for _, _, filename in all_images[:3]:
                print(f"Found: {filename}")
        
        if not image_paths:
            return {"success": False, "message": "Tidak ada gambar"}
        
        # Buat face vector
        add_face_start = time.time()
        face_vector_data = add_face_local(image_paths)
        add_face_time = time.time() - add_face_start
        
        # KONDISI YANG BENAR untuk mengecek face_vector_data
        if (face_vector_data is not None and 
            face_vector_data is not False and 
            len(face_vector_data) > 0):
            
            db_save_start = time.time()
            # Simpan ke database
            from .models import KompresiHuffman

            # SELALU BUAT RECORD BARU (TIDAK PERNAH UPDATE)
            from django.utils import timezone

            record = KompresiHuffman.objects.create(
                id_pegawai=str(id_pegawai),   
                width=0,
                height=0,
                frequency_model="{}",  # FIX: STRING
                code_table="{}",       # FIX: STRING
                compressed_file=b'',
                face_vector=json.dumps(face_vector_data),
                created_at=timezone.now()  # FIX: TIMEZONE
            ) 
            db_save_time = time.time() - db_save_start

            # Hitung total untuk user asli
            total_count = KompresiHuffman.objects.filter(
                id_pegawai__startswith=f"{id_pegawai}_"
            ).count()

            verify_start = time.time()
            
            # PANGGIL FUNCTION BARU
            verify_result = auto_verify_after_enrollment(record.id, str(id_pegawai), image_paths[0])
            verify_time = time.time() - verify_start

            verification_status = "✅ VERIFIED" if verify_result else "❌ FAILED"

            total_face_time = time.time() - start_time
            
            # ✅ BUAT TIMING SUMMARY
            server_timing = {
                'add_face_ms': round(add_face_time * 1000),
                'db_save_ms': round(db_save_time * 1000),
                'verify_ms': round(verify_time * 1000),
                'total_face_ms': round(total_face_time * 1000)
            }
            
            # ✅ SIMPAN TIMING LOG (OPSIONAL)
            if mobile_timing:
                try:
                    save_timing_to_db(id_pegawai, mobile_timing, server_timing, verify_result)
                except Exception as e:
                    print(f"⚠️ Failed to save timing log: {e}")

            return {
                "success": True, 
                "message": f"Face vector saved! {verification_status}", 
                "auto_verification": verify_result,
                "timing": {
                    "mobile": mobile_timing,
                    "server": server_timing
                },
                "kompresi_id": record.id
            }
        else:
            total_time = time.time() - start_time
            print(f"❌ Face vector creation failed after {total_time:.3f}s")
            return {"success": False, "message": "Failed to create face vector"}
                  
    except Exception as e:
        import traceback
        print(f"❌ Error: {str(e)}")
        traceback.print_exc()
        return {"success": False, "message": str(e)}

# MENYIMPAN HASIL WAKTUNYA
def save_timing_to_db(id_pegawai, mobile_timing, server_timing, verify_result, euclidean_distance=None, 
                      original_size=None, compressed_size=None):
    """Simpan timing data ke database"""
    try:
        from .models import TimingLog
        
        timing_log = TimingLog.objects.create(
            id_pegawai=id_pegawai,
            
            # Mobile timing
            mobile_capture=mobile_timing.get('capture_time'),
            mobile_huffman=mobile_timing.get('huffman_time'),
            mobile_sending=mobile_timing.get('sending_time'),
            mobile_total=mobile_timing.get('total_mobile_time'),
            
            # Server timing
            server_decode=server_timing.get('decode_time_ms'),
            server_add_face=server_timing.get('add_face_ms'),
            server_verify=server_timing.get('verify_ms'),
            server_total=server_timing.get('total_face_ms'),
            
            # Quality
            euclidean_distance=euclidean_distance,
            verification_success=verify_result,
            
            # File info
            original_size_bytes=original_size,
            compressed_size_bytes=compressed_size,
        )
        
        print(f"✅ Timing data saved with ID: {timing_log.id_timing}")
        return timing_log.id_timing
        
    except Exception as e:
        print(f"❌ Failed to save timing: {e}")
        import traceback
        traceback.print_exc()
        return None


@csrf_exempt 
def get_timing_stats(request):
    """API untuk statistik timing"""
    from .models import TimingLog 
    try:
        id_pegawai = request.GET.get('id_pegawai')
        
        if id_pegawai:
            logs = TimingLog.objects.filter(id_pegawai=id_pegawai)
        else:
            logs = TimingLog.objects.all()
        
        if not logs.exists():
            return JsonResponse({'error': 'No timing data found'}, status=404)
        
        from django.db.models import Avg
        # Hitung rata-rata
        total_logs = logs.count()
        avg_mobile = logs.aggregate(avg=Avg('mobile_total'))['avg'] or 0
        avg_server = logs.aggregate(avg=Avg('server_total'))['avg'] or 0
        success_count = logs.filter(verification_success=True).count()
        
        return JsonResponse({
            'status': 'success',
            'stats': {
                'total_requests': total_logs,
                'avg_mobile_time_ms': round(avg_mobile, 2),
                'avg_server_time_ms': round(avg_server, 2),
                'avg_total_time_ms': round(avg_mobile + avg_server, 2),
                'success_rate': round((success_count / total_logs) * 100, 2) if total_logs > 0 else 0
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def rle_decode_rgb(encoded_tuples, shape):
    """
    Decode RLE tuples menjadi array 3D RGB
    """
    height, width = shape
    decoded = []
    
    # Decode RLE untuk RGB
    for rgb_values, count in encoded_tuples:
        # rgb_values adalah [R, G, B]
        for _ in range(count):
            decoded.append(rgb_values)
    
    # Konversi ke numpy array
    decoded_array = np.array(decoded, dtype=np.uint8)
    
    # Validasi ukuran
    expected_size = height * width
    if len(decoded_array) != expected_size:
        raise ValueError(f"Decoded data size ({len(decoded_array)}) doesn't match expected size ({expected_size})")
    
    # Reshape ke bentuk gambar RGB (height, width, 3)
    return decoded_array.reshape(height, width, 3)

def rle_decode_grayscale(encoded_tuples, shape):
    """
    Decode RLE tuples menjadi array 2D grayscale (untuk backward compatibility)
    """
    height, width = shape
    decoded = []
    
    for value, count in encoded_tuples:
        decoded.extend([value] * count)
    
    decoded_array = np.array(decoded, dtype=np.uint8)
    
    expected_size = height * width
    if len(decoded_array) != expected_size:
        raise ValueError(f"Decoded data size ({len(decoded_array)}) doesn't match expected size ({expected_size})")
    
    return decoded_array.reshape(height, width)

# fiks ini kode untuk decode rle
@csrf_exempt
def rle_decode_image(request):
    import time  
    decode_start_time = time.time()

    if request.method != 'POST':
        return HttpResponseServerError("Invalid request method")

    try:
        # Parse JSON body
        body_unicode = request.body.decode('utf-8')
        body_data = json.loads(body_unicode)

        id_pegawai = body_data.get('id_pegawai')
        if not id_pegawai:
            return HttpResponseBadRequest("Missing id_pegawai field")
        
        compressed_b64 = body_data.get('compressed_data')
        shape = body_data.get('shape')
        channels = body_data.get('channels', 1)  # Default 1 untuk grayscale
        mode = body_data.get('mode', 'grayscale')  # Default grayscale

        if not compressed_b64 or not shape:
            return HttpResponseBadRequest("Missing 'compressed_data' or 'shape' fields in request")

        if not isinstance(shape, list) or len(shape) != 2:
            return HttpResponseBadRequest("Invalid 'shape' format")
        
        compressed_size = len(compressed_b64)

        # Decode base64 -> decompress gzip -> parse JSON
        compressed_bytes = base64.b64decode(compressed_b64)
        decompressed_bytes = gzip.decompress(compressed_bytes)
        decoded_payload = json.loads(decompressed_bytes.decode('utf-8'))

        encoded = decoded_payload.get('encoded')
        if not encoded:
            return HttpResponseBadRequest("Decoded payload missing 'encoded' field")

        rle_decode_start = time.time()

        # Proses berdasarkan mode (RGB atau grayscale)
        if mode.upper() == 'RGB' and channels == 3:
            print(f"Processing RGB image with shape: {shape}")
            
            # Untuk RGB, encoded_tuples berformat [[R,G,B], count]
            encoded_tuples = []
            for rgb_list, count in encoded:
                if len(rgb_list) != 3:
                    raise ValueError(f"Invalid RGB data: expected 3 values, got {len(rgb_list)}")
                encoded_tuples.append((rgb_list, int(count)))
            
            # Decode RLE RGB
            decoded_img = rle_decode_rgb(encoded_tuples, tuple(shape))
            
            # Konversi dari RGB ke BGR untuk OpenCV
            decoded_img_bgr = cv2.cvtColor(decoded_img, cv2.COLOR_RGB2BGR)
            
        else:
           
            # Untuk grayscale, encoded_tuples berformat [value, count]
            encoded_tuples = [(int(val), int(count)) for val, count in encoded]
            
            # Decode RLE grayscale
            decoded_img_bgr = rle_decode_grayscale(encoded_tuples, tuple(shape))

        rle_decode_time = time.time() - rle_decode_start

        if mode.upper() == 'RGB' and channels == 3:
            decoded_size = shape[0] * shape[1] * 3  # height x width x 3 channels
        else:
            decoded_size = shape[0] * shape[1]  # height x width

        # Siapkan direktori penyimpanan
        output_dir = os.path.join(settings.MEDIA_ROOT, "rle_images", str(id_pegawai))
        os.makedirs(output_dir, exist_ok=True)

        # Buat nama file berdasarkan waktu dan mode
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_rle.jpg"
        save_path = os.path.join(output_dir, filename)

        # Simpan sebagai gambar PNG
        success = cv2.imwrite(save_path, decoded_img_bgr)
        
        if not success:
            raise Exception("Failed to save image")

        # Informasi tambahan untuk response
        if mode.upper() == 'RGB':
            shape_info = f"{shape[0]}x{shape[1]}x{channels}"
        else:
            shape_info = f"{shape[0]}x{shape[1]}"

        # Ambil mobile_timing jika ada
        mobile_timing = body_data.get('mobile_timing')
        
        # ✅ PANGGIL FACE VECTOR RLE
        face_result = face_vector_rle(id_pegawai, save_path, mobile_timing)
        
        # ✅ TAMBAH: Hitung total waktu decoding
        total_decode_time = time.time() - decode_start_time

        response_data = {
            "message": "RLE decoded and face recognition completed",
            "decode_info": {
                "saved_path": save_path,
                "filename": filename,
                "original_shape": shape,
                "channels": channels,
                "mode": mode,
                "shape_info": shape_info
            },
            # ✅ TAMBAH: Data statistik untuk mobile
            "compressed_size": compressed_size,
            "decoded_size": decoded_size,
            "decompression_time_seconds": rle_decode_time,
            "total_decode_time_seconds": total_decode_time,

            "face_recognition": face_result,  # ← PINDAH KE SINI
            "status": "success"
        }

        return JsonResponse(response_data)

    except Exception as e:
        print(f"❌ Error in rle_decode_image: {str(e)}")
        return HttpResponseServerError(f"Error decoding image: {str(e)}")

def face_vector_rle(id_pegawai, latest_image_path=None, mobile_timing=None):
    import time
    start_time = time.time()

    try:
        import os
        import json
        from django.conf import settings
        from sipreti.face_recognition.main import add_face_local
        
        if mobile_timing:
            print(f"📱 RLE Mobile timing received: {mobile_timing}")

        # CARI FOLDER RLE IMAGES
        rle_folder = os.path.join(settings.MEDIA_ROOT, 'rle_images', str(id_pegawai))
        
        if not os.path.exists(rle_folder):
            return {"success": False, "message": "RLE folder tidak ditemukan"}
        
        # KUMPULKAN GAMBAR RLE - PRIORITASKAN GAMBAR TERBARU
        image_paths = []
        if latest_image_path and os.path.exists(latest_image_path):
            image_paths = [latest_image_path]
            print(f"🎯 Using latest RLE image: {os.path.basename(latest_image_path)}")
        else:
            # Ambil semua gambar RLE dan urutkan berdasarkan waktu
            all_images = []
            for filename in os.listdir(rle_folder):
                if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                    image_path = os.path.join(rle_folder, filename)
                    mtime = os.path.getmtime(image_path)
                    all_images.append((mtime, image_path, filename))
            
            # Urutkan berdasarkan waktu terbaru
            all_images.sort(reverse=True)
            
            # Ambil maksimal 3 gambar terbaru untuk efisiensi
            image_paths = [img[1] for img in all_images[:3]]
            
            for _, _, filename in all_images[:3]:
                print(f"Found RLE: {filename}")
        
        if not image_paths:
            return {"success": False, "message": "Tidak ada gambar RLE"}
        
        # BUAT FACE VECTOR (MENGGUNAKAN add_face_local YANG SAMA)
        add_face_start = time.time()
        print(f"🔄 Creating RLE face vector from {len(image_paths)} images...")
        face_vector_data = add_face_local(image_paths)
        add_face_time = time.time() - add_face_start
        
        # KONDISI YANG BENAR untuk mengecek face_vector_data
        if (face_vector_data is not None and 
            face_vector_data is not False and 
            len(face_vector_data) > 0):
            
            db_save_start = time.time()
            
            # SIMPAN KE DATABASE RLE
            from .models import KompresiRLE
            from django.utils import timezone

            # SELALU BUAT RECORD BARU (TIDAK PERNAH UPDATE)
            record = KompresiRLE.objects.create(
                id_pegawai=str(id_pegawai),   
                width=0,
                height=0,
                frequency_model="{}",  # FIX: STRING untuk RLE
                code_table="{}",       # FIX: STRING untuk RLE
                compressed_file=b'',
                face_vector=json.dumps(face_vector_data),
                created_at=timezone.now()  # FIX: TIMEZONE
            ) 
            db_save_time = time.time() - db_save_start

            # PANGGIL AUTO VERIFY RLE
            verify_start = time.time()
           
            # PANGGIL FUNCTION RLE BARU
            verify_result = auto_verify_after_enrollment_rle(record.id, str(id_pegawai), image_paths[0])
            verify_time = time.time() - verify_start

            verification_status = "✅ VERIFIED" if verify_result else "❌ FAILED"

            total_face_time = time.time() - start_time
            
            # ✅ BUAT TIMING SUMMARY RLE
            server_timing = {
                'add_face_ms': round(add_face_time * 1000),
                'db_save_ms': round(db_save_time * 1000),
                'verify_ms': round(verify_time * 1000),
                'total_face_ms': round(total_face_time * 1000)
            }
            
            return {
                "success": True, 
                "message": f"RLE face vector saved! {verification_status}", 
                "auto_verification": verify_result,
                "timing": {
                    "mobile": mobile_timing,
                    "server": server_timing
                },
                "kompresi_id": record.id,
                "compression_type": "RLE"
            }
        else:
            total_time = time.time() - start_time
            print(f"❌ RLE face vector creation failed after {total_time:.3f}s")
            return {"success": False, "message": "Failed to create RLE face vector"}
                  
    except Exception as e:
        import traceback
        print(f"❌ RLE face vector error: {str(e)}")
        traceback.print_exc()
        return {"success": False, "message": str(e)}


def auto_verify_after_enrollment_rle(record_id, id_pegawai, image_path):
    """
    Function RLE untuk auto verify setelah enrollment - MIRIP auto_verify_after_enrollment
    """
    try:
        import sipreti.face_recognition.main as main
        from django.conf import settings
        relative_path = os.path.relpath(image_path, settings.MEDIA_ROOT)
        image_url = f"http://localhost:8000{settings.MEDIA_URL}{relative_path.replace(os.sep, '/')}"
        
        
        # PANGGIL VERIFY_FACE_RLE (FUNCTION BARU DI MAIN)
        verify_result = main.verify_face_rle(image_url, str(id_pegawai))
        
        return verify_result
        
    except Exception as e:
        print(f"❌ RLE auto verify error: {e}")
        return False

@csrf_exempt
def encode_image(request):
    """Encode image using arithmetic coding"""
    if request.method != 'POST':
        return HttpResponseBadRequest("Only POST allowed")
    
    try:
        # Handle file upload
        if 'image' not in request.FILES:
            return JsonResponse({"error": "No image file provided"}, status=400)
        
        image_file = request.FILES['image']
        
        # Load and process image
        img = Image.open(image_file)
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        width, height = img.size
        
        # Convert image to pixel array
        pixels = []
        for y in range(height):
            for x in range(width):
                r, g, b = img.getpixel((x, y))
                pixels.extend([r, g, b])
        
        # Encode using arithmetic coding
        coder = ArithmeticCoder()
        encoded_bytes, freq_model = coder.encode(pixels)
        
        # Prepare response data
        encoded_data = base64.b64encode(encoded_bytes).decode('utf-8')
        
        response_data = {
            "status": "success",
            "encoded_data": encoded_data,
            "model": freq_model,
            "shape": [height, width, 3],
            "mode": "RGB",
            "original_size": len(pixels),
            "encoded_size": len(encoded_bytes),
            "compression_ratio": f"{len(pixels) / len(encoded_bytes):.2f}:1" if len(encoded_bytes) > 0 else "inf:1"
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def decode_image(request):
    """Decode image using arithmetic coding"""
    if request.method != 'POST':
        return HttpResponseBadRequest("Only POST allowed")

    try:
        data = json.loads(request.body.decode('utf-8'))
        encoded_data = data.get('encoded_data')
        model = data.get('model')
        shape = data.get('shape')
        mode = data.get('mode', 'RGB')

        if not (encoded_data and model and shape):
            return JsonResponse({"error": "Missing required data"}, status=400)

        # Convert model keys from string to int (JSON converts int keys to strings)
        freq_model = {int(k): v for k, v in model.items()}

        # Decode base64 to bytes
        bitstream = base64.b64decode(encoded_data)

        # Decode using arithmetic coding
        coder = ArithmeticCoder()
        decoded_pixels = coder.decode(bitstream, freq_model, np.prod(shape))

        # Reconstruct image array
        image_array = np.array(decoded_pixels, dtype=np.uint8).reshape(shape)

        # Create PIL Image
        if len(shape) == 3 and shape[2] == 3:
            pil_image = Image.fromarray(image_array, mode='RGB')
        elif len(shape) == 2:
            pil_image = Image.fromarray(image_array, mode='L')
        else:
            pil_image = Image.fromarray(image_array, mode='RGB')

        # Save decoded image
        decoded_dir = os.path.join(settings.MEDIA_ROOT, 'decoded_images')
        os.makedirs(decoded_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"arithmetic_decoded_{timestamp}.png"
        filepath = os.path.join(decoded_dir, filename)
        
        pil_image.save(filepath, 'PNG')
        image_url = f"{settings.MEDIA_URL}decoded_images/{filename}"

        return JsonResponse({
            "status": "success",
            "decoded_shape": list(image_array.shape),
            "image_saved": True,
            "image_url": image_url,
            "filename": filename,
            "decoded_pixels": len(decoded_pixels),
            "pixel_stats": {
                "min": int(np.min(image_array)),
                "max": int(np.max(image_array)),
                "mean": float(np.mean(image_array))
            }
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@api_view(['POST'])    
def daftar(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        nama = request.POST.get('nama')
        nip = request.POST.get('nip')
        no_hp = request.POST.get('no_hp')
        password = request.POST.get('password')
        email = request.POST.get('email')
        id_jabatan = request.POST.get('id_jabatan')
        id_unit_kerja = request.POST.get('id_unit_kerja')

        if not nip:
            return JsonResponse({'message': 'NIP wajib diisi'}, status=400)
        
        if Pegawai.objects.filter(nip=nip).exists():
            return JsonResponse({'message': 'NIP sudah terdaftar'}, status=400)
        
        if User.objects.filter(username=email).exists():
            return JsonResponse({'message': 'Email sudah terdaftar'}, status=400)

        try:
            jabatan_obj = Jabatan.objects.get(id_jabatan=id_jabatan)
        except Jabatan.DoesNotExist:
            return JsonResponse({'message': 'Jabatan tidak ditemukan'}, status=400)
        
        try:
            unit_kerja_obj = UnitKerja.objects.get(id_unit_kerja=id_unit_kerja)
        except UnitKerja.DoesNotExist:
            return JsonResponse({'message': 'Unit kerja tidak ditemukan'}, status=400)

        # Buat user
        user = User.objects.create(
            username=email,
            email=email,
            password=make_password(password),
        )

        # Buat pegawai
        Pegawai.objects.create(
            user=user,
            nama=nama,
            nip=nip,
            no_hp=no_hp,
            email=email,
            id_jabatan=jabatan_obj,
            id_unit_kerja=unit_kerja_obj,
        )

        return JsonResponse({'message': 'Akun berhasil dibuat'}, status=201)

    return JsonResponse({'message': 'Hanya menerima POST'}, status=405)

@csrf_exempt
@api_view(['POST'])
def login(request):

    if request.method == 'POST':
        try:
            data = request.data

            nip = data.get('nip')
            email = data.get('email')
            password = data.get('password')
            print(data)

            pegawai = Pegawai.objects.get(nip=nip, email=email)

            response_data = {
                "id_pegawai": pegawai.id_pegawai,
                "nama": pegawai.nama,
                "nip": pegawai.nip,
                "email": pegawai.email,
                "no_hp": pegawai.no_hp,
                "id_unit_kerja": pegawai.id_unit_kerja.pk if pegawai.id_unit_kerja else None,
            }

            return JsonResponse({"status": "success", "data": response_data}, status=200)

        except Pegawai.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Login gagal, data tidak ditemukan"}, status=401)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

# MWNGAMBIL DATA UNTUK DITAMPILKAN DI BAWAH PROFIL
def login_pegawai(request, id_pegawai):
    try:
        from .models import Pegawai
        
        # GUNAKAN SELECT_RELATED untuk JOIN otomatis
        pegawai = Pegawai.objects.select_related('id_jabatan', 'id_unit_kerja').get(
            id_pegawai=id_pegawai
        )
        
        response_data = {
            'id_pegawai': pegawai.id_pegawai,
            'nama': pegawai.nama,
            'nip': pegawai.nip,
            'id_jabatan': pegawai.id_jabatan.id if pegawai.id_jabatan else None,
            'nama_jabatan': pegawai.id_jabatan.nama_jabatan if pegawai.id_jabatan else None,
            'id_unit_kerja': pegawai.id_unit_kerja.id if pegawai.id_unit_kerja else None,
            'nama_unit_kerja': pegawai.id_unit_kerja.nama_unit_kerja if pegawai.id_unit_kerja else None,
        }
        
        return JsonResponse(response_data)
        
    except Pegawai.DoesNotExist:
        return JsonResponse({'error': 'Pegawai tidak ditemukan'}, status=404)


# DIGUNAKAN UNTUK AMBIL DATA CO/CI
def get_attendance(request, id_pegawai):
    try:
        from .models import LogAbsensi
        
        print(f"📊 Getting TODAY's LATEST attendance for pegawai: {id_pegawai}")
        
        # Ambil tanggal hari ini
        today = timezone.now().date()        
        # AMBIL CHECK-IN HARI INI YANG TERBARU
        today_latest_check_in = LogAbsensi.objects.filter(
            id_pegawai=id_pegawai,
            check_mode=0,  # Check-in
            waktu_absensi__date=today,  # HARI INI
            deleted_at__isnull=True
        ).order_by('-waktu_absensi').first()  # YANG TERBARU
        
        # AMBIL CHECK-OUT HARI INI YANG TERBARU
        today_latest_check_out = LogAbsensi.objects.filter(
            id_pegawai=id_pegawai,
            check_mode=1,  # Check-out
            waktu_absensi__date=today,  # HARI INI
            deleted_at__isnull=True
        ).order_by('-waktu_absensi').first()  # YANG TERBARU
       
        # RESPONSE SEDERHANA
        response_data = {
            'success': True,
            'id_pegawai': id_pegawai,
            'today': today.isoformat(),
            # Absensi hari ini yang terbaru
            'today_check_in': today_latest_check_in.waktu_absensi.isoformat() if today_latest_check_in else None,
            'today_check_out': today_latest_check_out.waktu_absensi.isoformat() if today_latest_check_out else None,
            # Status
            'has_checked_in_today': today_latest_check_in is not None,
            'has_checked_out_today': today_latest_check_out is not None,
            # Debug info
            'debug': {
                'total_checkins_today': LogAbsensi.objects.filter(
                    id_pegawai=id_pegawai, 
                    check_mode=0, 
                    waktu_absensi__date=today,
                    deleted_at__isnull=True
                ).count(),
                'total_checkouts_today': LogAbsensi.objects.filter(
                    id_pegawai=id_pegawai, 
                    check_mode=1, 
                    waktu_absensi__date=today,
                    deleted_at__isnull=True
                ).count(),
            }
        }
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"❌ Error getting today's attendance: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': 'Gagal mengambil data absensi hari ini'
        }, status=500)


#  DIGUNAKAN UNTUK EDIT INFORMASI PEGAWAI DI BAGIAN AKUN
def get_pegawai_detail(request, id_pegawai):
    try:
        pegawai = Pegawai.objects.get('id_jabatan', 'id_unit_kerja').get(id_pegawai=id_pegawai)
        
        # ✅ Langsung ambil dari field database
        data = {
            'id_pegawai': pegawai.id_pegawai,
            'nama': pegawai.nama,
            'nip': pegawai.nip, 
            'jabatan': pegawai.id_jabatan.nama_jabatan if pegawai.id_jabatan else 'Tidak Diset',
            'unit_kerja': pegawai.id_unit_kerja.nama_unit_kerja if pegawai.id_unit_kerja else 'Tidak Diset',
            'email': pegawai.email,     # ← Dari kolom email
            'no_hp': pegawai.no_hp,     # ← Dari kolom no_hp
            'foto': pegawai.foto.url if pegawai.foto else None,
        }
        
        return JsonResponse({'status': 'success', 'data': data})
    except Pegawai.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Pegawai tidak ditemukan'})
    
#  DIGUNAKAN UNTUK EDIT INFORMASI PEGAWAI DI BAGIAN AKUN
def update_pegawai_info(request, id_pegawai):
    if request.method == 'PUT':
        try:
            pegawai = Pegawai.objects.get(id_pegawai=id_pegawai)
            data = json.loads(request.body)
            
            # Update langsung ke kolom database
            if 'nama' in data:
                pegawai.nama = data['nama']
            if 'email' in data:
                pegawai.email = data['email'] if data['email'] else None
            if 'no_hp' in data:
                pegawai.no_hp = data['no_hp'] if data['no_hp'] else None
                
            pegawai.save()
            
            return JsonResponse({'status': 'success', 'message': 'Data berhasil diperbarui'})
        except:
            return JsonResponse({'status': 'error', 'message': 'Gagal update'})
        
@api_view(['POST'])
def log_absensi(request):
    print("Data diterima:", request.data)

    id_pegawai = request.data.get('id_pegawai')
    jenis = request.data.get('jenis', 0)
    lokasi = request.data.get('lokasi')
    waktu = timezone.now()
    check_mode = request.data.get('check_mode')
    latitude = request.data.get('latitude')
    longitude = request.data.get('longitude')

    print("jenis =", jenis)
    print("check_mode =", check_mode)

    if check_mode not in [0, 1, '0', '1']:
        return Response({'message': 'check_mode tidak valid'}, status=400)
    
    try:
        # Ambil objek pegawai berdasarkan ID
        pegawai = Pegawai.objects.get(id_pegawai=id_pegawai)
    except Pegawai.DoesNotExist:
        return Response({'message': 'Pegawai tidak ditemukan'}, status=404)

    # Simpan ke model Absensi
    LogAbsensi.objects.create(
        id_pegawai=pegawai,
        jenis_absensi=jenis,
        nama_lokasi=lokasi,
        waktu_absensi=waktu,
        check_mode=check_mode, 
        latitude=latitude,
        longitude=longitude,       
    )

    try:
        requests.post('http://localhost:8080/sipreti/log_absensi', data={
            'id_pegawai': id_pegawai,
            'jenis_absensi': jenis,
            'check_mode': check_mode,
            'nama_lokasi': lokasi,
            'waktu_absensi': waktu.isoformat(),
            'latitude': latitude,
            'longitude': longitude,
    })

    except Exception as e:
        print('Gagal kirim ke CI:', e)

    return Response({'message': 'Berhasil disimpan'}, status=200)

@api_view(['POST'])
def register_android_device(request):
    try:
        # Ambil data dari request
        data = request.data
        id_pegawai = data.get('id_pegawai')
        username = data.get('username')
        device_id = data.get('device_id')
        device_brand = data.get('device_brand')
        device_model = data.get('device_model')
        device_os_version = data.get('device_os_version')
        device_sdk_version = data.get('device_sdk_version')
        last_login = data.get('last_login')
        
        try:
            pegawai = Pegawai.objects.get(id_pegawai=id_pegawai)
        except Pegawai.DoesNotExist:
            return Response({'status': 'error', 'message': f'Pegawai dengan ID {id_pegawai} tidak ditemukan'}, status=404)
        
        # Simpan ke database
        user_android = UserAndroid.objects.create(
            id_pegawai=pegawai,
            username=username,
            device_id=device_id,
            device_brand=device_brand,
            device_model=device_model,
            device_os_version=device_os_version,
            device_sdk_version=device_sdk_version,
            last_login=last_login
        )
        
        return Response({'status': 'success', 'id': user_android.id}, status=201)
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=400)

@api_view(['GET'])
def get_radius(request):
    try:
        radius_list = RadiusAbsen.objects.all()
        data = []
        for r in radius_list:
            data.append({
                'id_radius': r.id_radius,
                'ukuran': r.ukuran,
                'satuan': r.satuan,
            })
        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)
    

@api_view(['GET'])
def get_lokasi_unit_kerja(request):
    try:
        unit_list = UnitKerja.objects.all()
        data = []
        for unit in unit_list:
            data.append({
                'id_unit_kerja': unit.id_unit_kerja,
                'nama_unit': unit.nama_unit,
                'alamat': unit.alamat,
                'radius': {
                    'id_radius': unit.radius.id_radius if unit.radius else None,
                    'ukuran': unit.radius.ukuran if unit.radius else None,
                    'satuan': unit.radius.satuan if unit.radius else None,
                }
            })
        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@csrf_exempt
def enroll_face(request):
    if request.method == 'POST':
        if 'url_foto' in request.FILES and 'id_pegawai' in request.POST:
            file = request.FILES['url_foto']
            id_pegawai = request.POST['id_pegawai']
            file_name = file.name

            # Simpan file secara lokal
            url_image = save_uploaded_file(file)

            # Generate vektor
            success = add_face([url_image], id_pegawai)

            if success:
                face_id = insert_image_db(id_pegawai, file_name, url_image)
                return JsonResponse({
                    'status': 1,
                    'message': 'Vektor berhasil dibuat',
                    'face_id': face_id,
                    'url': url_image
                })
            else:
                return JsonResponse({
                    'status': 0,
                    'message': 'Gagal mendeteksi wajah'
                })
        else:
            return JsonResponse({
                'status': 0,
                'message': 'Data tidak lengkap'
            })
    return JsonResponse({'status': 0, 'message': 'Gunakan metode POST'})

# Definisi class HuffmanNode
class HuffmanNode:
    def __init__(self, value=None, frequency=0):
        self.value = value
        self.frequency = frequency
        self.left = None
        self.right = None

# Fungsi helper untuk membangun pohon Huffman dari JSON
def build_huffman_tree_from_json(json_data):
    """
    Membangun pohon Huffman dari format JSON yang dikirim oleh Flutter
    """
    if json_data is None:
        return None
    
    # Format array dari serialisasi optimized
    if isinstance(json_data, list):
        def build_tree_from_array(array, index=0):
            if index >= len(array) or array[index] == -1:
                return None, index + 1
            
            if array[index] >= 0:  # Leaf node
                return HuffmanNode(value=array[index]), index + 1
            
            # Internal node (-2)
            node = HuffmanNode()
            index += 1
            
            node.left, index = build_tree_from_array(array, index)
            node.right, index = build_tree_from_array(array, index)
            
            return node, index
        
        root, _ = build_tree_from_array(json_data)
        return root
    
    # Format dictionary/object dengan left/right
    if isinstance(json_data, dict):
        node = HuffmanNode(
            value=json_data.get("value"),
            frequency=json_data.get("frequency", 0)
        )
        
        if "left" in json_data and json_data["left"] is not None:
            node.left = build_huffman_tree_from_json(json_data["left"])
        
        if "right" in json_data and json_data["right"] is not None:
            node.right = build_huffman_tree_from_json(json_data["right"])
        
        return node
    
    # Format tidak dikenali
    raise ValueError(f"Unrecognized Huffman tree format: {json_data}")

# Fungsi untuk melakukan dekode Huffman
def huffman_decode(encoded_data, huffman_tree, shape):
    try:
        # Jika encoded_data adalah string base64, decode dulu
        if isinstance(encoded_data, str):
            encoded_bytes = base64.b64decode(encoded_data)
        else:
            encoded_bytes = encoded_data
        
        # Konversi data terkompresi ke bitstream
        bitstream = []
        for i in range(len(encoded_bytes) - 1):  # Abaikan byte terakhir (padding)
            byte = encoded_bytes[i]
            for j in range(7, -1, -1):
                bit = (byte >> j) & 1
                bitstream.append(bit)
        
        # Cek padding bits di byte terakhir
        if len(encoded_bytes) > 0:
            padding_bits = encoded_bytes[-1]
            if padding_bits < 8:
                # Tambahkan bit dari byte terakhir kecuali padding
                byte = encoded_bytes[-2] if len(encoded_bytes) > 1 else 0
                for j in range(7, padding_bits - 1, -1):
                    bit = (byte >> j) & 1
                    bitstream.append(bit)
        
        # Decode bitstream menggunakan pohon Huffman
        decoded_pixels = []
        current_node = huffman_tree
        
        for bit in bitstream:
            if bit == 0:
                current_node = current_node.left
            else:
                current_node = current_node.right
            
            # Jika leaf node (tidak punya anak)
            if current_node is not None and current_node.left is None and current_node.right is None:
                decoded_pixels.append(current_node.value)
                current_node = huffman_tree  # Reset ke root
        
        # Pastikan jumlah pixel sesuai dengan dimensi
        expected_pixels = shape[0] * shape[1]
        
        if len(decoded_pixels) < expected_pixels:
            print(f"Warning: Pixel kurang. Got {len(decoded_pixels)}, expected {expected_pixels}")
            # Padding dengan nilai 0 jika kurang
            decoded_pixels.extend([0] * (expected_pixels - len(decoded_pixels)))
        elif len(decoded_pixels) > expected_pixels:
            print(f"Warning: Pixel berlebih. Got {len(decoded_pixels)}, expected {expected_pixels}")
            # Potong jika berlebih
            decoded_pixels = decoded_pixels[:expected_pixels]
        
        # Konversi ke array 2D untuk gambar
        # Perhatikan shape: Django mengharapkan (height, width)
        decoded_image = np.array(decoded_pixels, dtype=np.uint8).reshape(shape)
        
        return decoded_image
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error in huffman_decode: {e}")
        raise

def fix_base64_padding(base64_string):
    """Memperbaiki padding base64 jika tidak lengkap"""
    # Base64 harus memiliki panjang yang merupakan kelipatan 4
    missing_padding = len(base64_string) % 4
    if missing_padding:
        base64_string += '=' * (4 - missing_padding)
    return base64_string



# KOMPRESI HUFFMAN (MENJADIKAN DECODE)
# Endpoint untuk menerima data dan melakukan dekompresi
@csrf_exempt
def upload_encoded_huffman_image(request):
    """
    Endpoint untuk menerima data kompresi Huffman dan melakukan dekompresi
    """
    import time
    from django.core.files.base import ContentFile
    from django.utils import timezone
    from .models import KompresiHuffman
    from django.core.files import File
    start_time = time.time()

    if request.method != "POST":
        return HttpResponseBadRequest("Invalid method")

    try:
        # Tambahkan log untuk debugging
        print("Received request for Huffman decoding")
        
        # Ambil JSON dari body request
        data = json.loads(request.body)
        
        # Log data yang diterima
        print(f"Request data keys: {data.keys()}")
        
        mobile_timing = {
            'capture_time_s': (data.get('capture_time', 0) or 0) / 1000,
            'huffman_time_s': (data.get('huffman_time', 0) or 0) / 1000, 
            'sending_time_s': (data.get('sending_time', 0) or 0) / 1000 if data.get('sending_time') else None,
            'total_mobile_time_s': (data.get('total_mobile_time', 0) or 0) / 1000 if data.get('total_mobile_time') else None
        }

        # TAMBAHKAN INI: Ambil id_pegawai dari data
        id_pegawai = data.get("id_pegawai")
        is_rgb = data.get("is_rgb", True)
        print(f"Is RGB image: {is_rgb}")

        decode_start = time.time()

        if is_rgb:
            # PERUBAHAN: Terima data dengan format yang lebih sederhana
            print("Processing RGB image with simple format")
            
            decode_start = time.time()
            # Ambil data
            shape = tuple(data.get("shape", [0, 0]))  # Fallback to [0, 0] if missing
            if len(shape) != 2 or shape[0] <= 0 or shape[1] <= 0:
                return HttpResponseBadRequest(f"Invalid shape: {shape}. Expected [height, width] with positive values.")
        
            height, width = shape

            # PERBAIKAN: Periksa apakah semua data yang dibutuhkan tersedia
            required_keys = ['red_encoded', 'green_encoded', 'blue_encoded', 
                             'red_root', 'green_root', 'blue_root']
            for key in required_keys:
                if key not in data:
                    print(f"Missing required data: {key}")
                    return HttpResponseBadRequest(f"Missing required data: {key}")
            
            # Ambil encoded data dan root
            red_encoded = data.get("red_encoded", "")
            green_encoded = data.get("green_encoded", "")
            blue_encoded = data.get("blue_encoded", "")
            
            red_root_base64 = data.get("red_root", "")
            green_root_base64 = data.get("green_root", "")
            blue_root_base64 = data.get("blue_root", "")
         
            # 🗄️ HITUNG DATA UNTUK DATABASE
            original_pixels = height * width
            original_size_bytes = original_pixels * 3  # RGB = 3 bytes per pixel
            compressed_size_bytes = len(red_encoded) + len(green_encoded) + len(blue_encoded)
            compression_time_s = mobile_timing.get('huffman_time_s', 0) or 0
         
            # Fungsi untuk memperbaiki padding base64
            def fix_base64_padding(s):
                missing_padding = len(s) % 4
                if missing_padding:
                    s += '=' * (4 - missing_padding)
                return s
            
            # Decode data
            try:
                # Perbaiki padding dan decode base64
                red_root_base64 = fix_base64_padding(red_root_base64)
                green_root_base64 = fix_base64_padding(green_root_base64)
                blue_root_base64 = fix_base64_padding(blue_root_base64)
                
                red_root_bytes = base64.b64decode(red_root_base64)
                green_root_bytes = base64.b64decode(green_root_base64)
                blue_root_bytes = base64.b64decode(blue_root_base64)
                
                # Parse JSON untuk root
                red_root_json = red_root_bytes.decode('utf-8')
                green_root_json = green_root_bytes.decode('utf-8')
                blue_root_json = blue_root_bytes.decode('utf-8')
                
                red_root = json.loads(red_root_json)
                green_root = json.loads(green_root_json)
                blue_root = json.loads(blue_root_json)
                
                # Build Huffman trees
                red_huff_root = build_huffman_tree_from_json(red_root)
                green_huff_root = build_huffman_tree_from_json(green_root)
                blue_huff_root = build_huffman_tree_from_json(blue_root)
                
                # Dekode setiap channel
                red_channel = huffman_decode(red_encoded, red_huff_root, shape)
                green_channel = huffman_decode(green_encoded, green_huff_root, shape)
                blue_channel = huffman_decode(blue_encoded, blue_huff_root, shape)
                
                # Tambahkan setelah log chars
                red_bits = len(red_encoded)
                green_bits = len(green_encoded)  
                blue_bits = len(blue_encoded)
                total_bits = red_bits + green_bits + blue_bits

                # Original vs compressed
                original_bytes = height * width * 3
                compressed_bytes = total_bits / 8
                compression_ratio = (1 - (compressed_bytes / original_bytes)) * 100

                # Validasi ukuran channel
                expected_channel_size = height * width
                for channel_name, channel in [("Red", red_channel), ("Green", green_channel), ("Blue", blue_channel)]:
                    if channel.shape != (height, width):
                        print(f"❌ {channel_name} channel size mismatch!")
                        print(f"   Expected: {(height, width)} -> Got: {channel.shape}")
                    if channel.nbytes != expected_channel_size:
                        print(f"⚠️ {channel_name} channel byte count mismatch!")
                        print(f"   Expected: {expected_channel_size:,} -> Got: {channel.nbytes:,}")

                # Gabungkan ketiga channel
                height, width = shape
                decoded_image = np.zeros((height, width, 3), dtype=np.uint8)
                decoded_image[:, :, 0] = blue_channel  # B channel (OpenCV uses BGR)
                decoded_image[:, :, 1] = green_channel # G channel
                decoded_image[:, :, 2] = red_channel   # R channel
 
            except Exception as e:
                print(f"Error during RGB decoding: {e}")
                import traceback
                traceback.print_exc()
                return HttpResponseBadRequest(f"Error during RGB decoding: {e}")
        
            decode_time = time.time() - decode_start
    
        # Buat folder huffman_images jika belum ada
        output_dir = os.path.join(settings.MEDIA_ROOT, "huffman_images", str(id_pegawai))
        os.makedirs(output_dir, exist_ok=True)

        # Buat nama file berdasarkan waktu
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_huffman.jpg"
        save_path = os.path.join(output_dir, filename)

        # Simpan gambar
        cv2.imwrite(save_path, decoded_image)
        print(f"Image saved to: {save_path}")
        
        face_start = time.time() 
        
        # PASS TIMING DATA KE FACE_VECTOR
        result = face_vector(id_pegawai, save_path, mobile_timing)# Pass path gambar terbaru
        print(f"Face vector result: {result}")

        face_time = time.time() - face_start  
        total_server_time = time.time() - start_time  
        
        # Tambahan: total keseluruhan
        total_mobile_time = sum([t for t in [mobile_timing.get('capture_time_s', 0), 
                                           mobile_timing.get('huffman_time_s', 0), 
                                           mobile_timing.get('sending_time_s', 0)] if t])
        total_process_time = total_mobile_time + total_server_time
        
        # URL untuk akses gambar
        media_url = f"{settings.MEDIA_URL.rstrip('/')}/huffman_images/{id_pegawai}/{filename}"

         # 🗄️ SIMPAN KE DATABASE
        try:
            # Siapkan file untuk ImageField
            with open(save_path, 'rb') as img_file:
                django_file = File(img_file)
                
                # Buat instance model
                huffman_record = KompresiHuffman(
                    id_pegawai=str(id_pegawai),
                    width=width,
                    height=height,
                    compression_type='huffman',
                    original_length=original_pixels,  # Total pixels
                    original_size=original_size_bytes,  # Ukuran asli dalam bytes
                    compressed_size=compressed_size_bytes,  # Ukuran terkompresi
                    compression_ratio=compression_ratio,  # Rasio kompresi dalam persen
                    compression_time_ms=int(compression_time_s * 1000),  # Waktu kompresi dari mobile
                    face_vector=result.get('face_vector', '') if result.get("success") else '',  # Face vector dari hasil face processing
                    code_table=f"huffman_compression_{width}x{height}_{timezone.now().strftime('%Y%m%d_%H%M%S')}",
                    created_at=timezone.now()
                )
                
                # Simpan file gambar ke ImageField
                relative_path = f"huffman_images/{id_pegawai}/{filename}"
                huffman_record.hasil_uncompress.save(
                    filename,
                    django_file,
                    save=False  # Jangan save dulu, kita akan save manual
                )
                
                # Simpan ke database
                huffman_record.save()
                
        except Exception as db_error:
            print(f"❌ Error menyimpan ke database: {db_error}")
            import traceback
            traceback.print_exc()

        # PERBAIKAN: RETURN HASIL DARI FACE_VECTOR, BUKAN RESPONSE UPLOAD
        if result.get("success"):
            # Tambahkan info file ke hasil face_vector
            result["timing"] = {
                "mobile": {
                    "capture_time_s": mobile_timing.get('capture_time_s', 0),
                    "huffman_time_s": mobile_timing.get('huffman_time_s', 0),
                    "sending_time_s": mobile_timing.get('sending_time_s'),
                    "total_mobile_time_s": total_mobile_time
                },
                "server": {
                    "decode_time_s": round(decode_time, 3),
                    "face_processing_s": round(face_time, 3), 
                    "total_server_s": round(total_server_time, 3)
                },
                "total": {
                    "total_process_s": round(total_process_time, 3)
                }
            }
            result["filename"] = filename
            result["path"] = save_path 
            result["url"] = media_url
            
            result["decompression_time_seconds"] = round(decode_time, 3)  # Waktu dekompresi dalam detik
            result["decoded_size"] = int(decoded_image.nbytes)  # Ukuran hasil decode dalam bytes

            # TAMBAHKAN EUCLIDEAN DISTANCE INFO
            if 'euclidean_distance' in result:
                result["face_recognition"] = {
                    "euclidean_distance": result.get('euclidean_distance'),
                    "face_threshold": result.get('face_threshold', 0.6),  # atau ambil dari settings
                    "verification_passed": result.get('verification_passed', False),
                    "distance_quality": get_quality_level(result.get('euclidean_distance', 999))
                }
                
                # Print untuk debugging (sama seperti di Django log)
                distance = result.get('euclidean_distance')
                  
            # 📏 TAMBAHKAN INFO UKURAN KE RESPONSE
            result["size_info"] = {
                "mobile_shape": list(shape),
                "server_shape": list(decoded_image.shape),
                "total_bytes": int(decoded_image.nbytes),
                "compression_ratio": round(compression_ratio, 2),
                "per_channel_bytes": int(expected_channel_size)
            }
            return JsonResponse(result)
        else:
            # Jika face_vector gagal, return error
            print(f"❌ DEBUG: face_vector failed: {result}")
            return JsonResponse(result, status=400)

    except Exception as e:
        import traceback
        print(f"Error in upload_encoded_huffman_image: {e}")
        traceback.print_exc()
        return HttpResponseBadRequest(str(e))

def unit_kerja_list(request):
    radius_aktif = RadiusAbsen.objects.filter(is_active=True).first()

    if radius_aktif:
        # Update semua unit kerja untuk pakai radius aktif
        UnitKerja.objects.update(radius=radius_aktif) 

    data = list(UnitKerja.objects.select_related('radius').values(
        'id_unit_kerja', 
        'nama_unit_kerja', 
        'latitude',
        'longitude',
        'radius',
    ))
    
    # Ganti nama key agar tetap 'radius'
    for item in data:
        item['radius'] = radius_aktif.ukuran if radius_aktif else 0
    
    return JsonResponse(data, safe=False)

def unit_kerja_detail(request, id_unit_kerja):
    """Endpoint untuk mengambil unit kerja spesifik berdasarkan ID"""
    try:
        radius_aktif = RadiusAbsen.objects.filter(is_active=True).first()
        
        if radius_aktif:
            UnitKerja.objects.update(radius=radius_aktif)
        unit_kerja = get_object_or_404(UnitKerja, id_unit_kerja=id_unit_kerja)
        
        # Format data response
        data = {
            'id_unit_kerja': unit_kerja.id_unit_kerja,
            'nama_unit_kerja': unit_kerja.nama_unit_kerja,
            'latitude': unit_kerja.latitude,
            'longitude': unit_kerja.longitude,
            'radius': radius_aktif.ukuran if radius_aktif else 0,
        }
        
        return JsonResponse(data, safe=False)
        
    except UnitKerja.DoesNotExist:
        return JsonResponse({
            'error': f'Unit kerja dengan ID {id_unit_kerja} tidak ditemukan'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'error': f'Terjadi kesalahan: {str(e)}'
        }, status=500)

@api_view(['GET'])
def jabatan_list(request):
    data = list(Jabatan.objects.values('id_jabatan', 'nama_jabatan'))
    return JsonResponse(data, safe=False)

def get_detail_json(request, id):
    try:
        radius = RadiusAbsen.objects.get(pk=id)
        data = {
            'id': radius.id,
            'radius': radius.radius,
            'satuan': radius.satuan
        }
        return JsonResponse(data)
    except RadiusAbsen.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)

# KOMPRESI RLE
@csrf_exempt
def kompresi_rle(request):
    if request.method == 'POST':
        try:
            id_pegawai = request.POST.get('id_pegawai')
            width = int(request.POST.get('width'))
            height = int(request.POST.get('height'))
            original_length = int(request.POST.get('original_length'))
            compression_type = request.POST.get('compression_type')
            
            # Metrik kompresi
            original_size = int(request.POST.get('original_size', 0))
            compressed_size = int(request.POST.get('compressed_size', 0))
            compression_ratio = float(request.POST.get('compression_ratio', 1.0))
            compression_time_ms = int(request.POST.get('compression_time_ms', 0))
            
            # Field yang mungkin kosong untuk RLE
            frequency_model = request.POST.get('frequency_model', '{}')
            code_table = request.POST.get('code_table', '{}')
            
            # Cek apakah file ada
            if 'compressed_file' not in request.FILES:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No compressed file provided'
                }, status=400)
            
            compressed_file = request.FILES['compressed_file']
            
            # Cek apakah ini RGB atau grayscale
            is_rgb = request.POST.get('is_rgb', '') == 'true'
            
            # Buat dan simpan objek kompresi
            kompresi = Kompresi(
                id_pegawai=id_pegawai,
                width=width,
                height=height,
                original_length=original_length,
                compression_type=compression_type,
                original_size=original_size,
                compressed_size=compressed_size,
                compression_ratio=compression_ratio,
                compression_time_ms=compression_time_ms,
                frequency_model=json.loads(frequency_model),
                code_table=json.loads(code_table),
                is_rgb=is_rgb,
                compressed_file=compressed_file
            )
            kompresi.save()
            
            return JsonResponse({
                'status': 'success',
                'kompresi_id': kompresi.id
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=405)

# update data diri di mobile
@csrf_exempt
def update_pegawai(request, id_pegawai):
    if request.method != 'PUT':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
    
    try:
        pegawai = get_object_or_404(Pegawai, id_pegawai=id_pegawai, deleted_at__isnull=True)
        data = json.loads(request.body)
        
        # Update data
        pegawai.nama = data.get('nama', pegawai.nama)
        pegawai.email = data.get('email', pegawai.email)
        pegawai.no_hp = data.get('no_hp', pegawai.no_hp)
        pegawai.save()
        
        # Update User juga
        if pegawai.user:
            pegawai.user.first_name = pegawai.nama
            pegawai.user.email = pegawai.email
            pegawai.user.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Data berhasil diperbarui',
            'data': {
                'id_pegawai': pegawai.id_pegawai,
                'nama': pegawai.nama,
                'email': pegawai.email,
                'no_hp': pegawai.no_hp,
                'nip': pegawai.nip,
                'jabatan': pegawai.id_jabatan.nama_jabatan if pegawai.id_jabatan else 'Tidak Diset',
                'unit_kerja': pegawai.id_unit_kerja.nama_unit_kerja if pegawai.id_unit_kerja else 'Tidak Diset',
            }
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)