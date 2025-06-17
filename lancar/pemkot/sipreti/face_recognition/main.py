import cv2
from .align_custom import AlignCustom
from .face_feature import FaceFeature
from .mtcnn_detect import MTCNNDetect
from .tf_graph import FaceRecGraph
import argparse
import sys
import json
import time
import numpy as np
from urllib.request import urlopen
TIMEOUT = 10 #10 seconds
from numpy import array
import os
from django.conf import settings
import pymysql

path_dataset = settings.MEDIA_ROOT+"/sipreti/dataset/"

def create_empty_dataset(path):
    dir = os.path.dirname(path)
    if not os.path.exists(dir):
        os.makedirs(dir)
    if not os.path.exists(path):
        f = open(path,'w+')
        f.write("{}")
    else:
        os.remove(path)
        f = open(path,'w+')
        f.write("{}")
    
def verify_face(url_image,id_pegawai):
    FRGraph = FaceRecGraph()
    MTCNNGraph = FaceRecGraph()
    aligner = AlignCustom()
    extract_feature = FaceFeature(FRGraph)
    face_detect = MTCNNDetect(MTCNNGraph, scale_factor=2) 
    
    # print("get photo...")
    # vs = cv2.VideoCapture(0) #get input from webcam
    detect_time = time.time()
    req = urlopen(url_image)
    arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
    frame = cv2.imdecode(arr, -1) # 'Load it as it is'
    #u can certainly add a roi here but for the sake of a demo i'll just leave it as simple as this
    try:
        # print("get landmark")
        rects, landmarks = face_detect.detect_face(frame,80)#min face size is set to 80x80
    except:
        # print("gagal get landmark")
        return False
    aligns = []
    positions = []

    for (i, rect) in enumerate(rects):
        aligned_face, face_pos = aligner.align(160,frame,landmarks[:,i])
        if len(aligned_face) == 160 and len(aligned_face[0]) == 160:
            aligns.append(aligned_face)
            positions.append(face_pos)
        else: 
            print("Align face failed") #log  
    # print("reconigzed")      
    # print(len(aligns))
    if(len(aligns) > 0):
        features_arr = extract_feature.get_features(aligns)
        recog_data = findPeople(features_arr,positions,id_pegawai)
        return recog_data

def findPeople(features_arr, positions, id_pegawai, thres = 0.6, percent_thres = 70):
    print(f"🔍 Looking for biometrik data for: {id_pegawai}")
    try:
        
        import sys
        import numpy as np
        import json
        from sipreti.models import KompresiHuffman
        
        # FIX: Handle multiple records safely

         # Cari di KompresiHuffman table
        huffman_records = KompresiHuffman.objects.filter(id_pegawai=str(id_pegawai))
        
        if huffman_records.count() == 0:
            print("Employee not found in KompresiHuffman")
            return False
        
        print(f"✅ Found {huffman_records.count()} records in KompresiHuffman")
        
        # Ambil record terbaru
        latest_record = huffman_records.order_by('-id').first()
        
        if not latest_record.face_vector:
            print("No face vector stored in latest record")
            return False
        
        # Parse face vector data
        face_vector_data = json.loads(latest_record.face_vector)
        
        if isinstance(face_vector_data, dict) and "Center" in face_vector_data:
            # Format: {"Center": [[vector1], [vector2], ...]}
            center_vectors = face_vector_data["Center"]
            print(f"✅ Found Center data with {len(center_vectors)} vectors")
        elif isinstance(face_vector_data, list) and len(face_vector_data) == 128:
            # Format: langsung array [128D]
            center_vectors = [face_vector_data]  # Wrap dalam array
            print("✅ Single vector converted to Center format")
        else:
            print(f"❌ Invalid face vector format: {type(face_vector_data)}")
            return False
        
    except json.JSONDecodeError as je:
        print(f"Invalid JSON format in face_vector: {je}")
        return False
    except Exception as e:
        print(f"KompresiHuffman error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Proses comparison (tetap sama seperti sebelumnya)
    print(f"🔄 Starting comparison for {len(features_arr)} faces")

    for (i, features_128D) in enumerate(features_arr):
        smallest = sys.maxsize
        print(f"🔄 Processing face #{i+1}")
        
        for j, stored_vector in enumerate(center_vectors):
            distance = np.sqrt(np.sum(np.square(np.array(stored_vector) - np.array(features_128D))))
            print(f"   Distance to stored vector {j+1}: {distance:.4f}")
            
            if distance < smallest:
                smallest = distance
                print(f"   ✅ New best distance: {smallest:.4f}")

        if smallest <= thres:  # Jika distance <= 0.6 (threshold)
            percentage = max(0, 100 * (1 - (smallest / thres)))
        else:
            percentage = 0
        print(f"📊 Best distance: {smallest:.4f}")
        print(f"📊 Percentage: {percentage:.2f}%")
        print(f"📊 Threshold: {percent_thres}%")

        if percentage <= percent_thres:
            print(f"❌ WAJAH TIDAK MIRIP: {percentage:.2f}% <= {percent_thres}%")
            return False
        else:
            print(f"✅ WAJAH MIRIP: {percentage:.2f}% > {percent_thres}%")
            
    print("✅ Semua wajah yang terdeteksi mirip dengan data tersimpan!")
    return True

def add_face(url_image_list):
    import json
    
    FRGraph = FaceRecGraph()
    MTCNNGraph = FaceRecGraph()
    aligner = AlignCustom()
    extract_feature = FaceFeature(FRGraph)
    face_detect = MTCNNDetect(MTCNNGraph, scale_factor=2) 

    person_imgs = {"Left" : [], "Right": [], "Center": []}
    person_features = {"Left" : [], "Right": [], "Center": []}
    no = 0
    for(url_image) in url_image_list:
        # print(no)
        no += 1
        print(f"Processing image {no}: {url_image}")

        try:
            req = urlopen(url_image)
            arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
            frame = cv2.imdecode(arr, -1) # 'Load it as it is'
        except Exception as e:
            print(f"Gagal buka URL {url_image}:", e)
            continue

        try:
            print("Getting landmark...")
            rects, landmarks = face_detect.detect_face(frame, 80)  # min face size is set to 80x80
        except:
          print("Gagal deteksi wajah:", e)
          continue
        
        if(len(rects)==0):
            print("Tidak ada wajah terdeteksi.")
            continue
        
        for (i, rect) in enumerate(rects):
            aligned_frame, pos = aligner.align(160,frame,landmarks[:,i])
            if len(aligned_frame) == 160 and len(aligned_frame[0]) == 160:
                person_imgs[pos].append(aligned_frame)
    
    total_images = sum(len(person_imgs[pos]) for pos in person_imgs)
    if total_images == 0:
        print("Tidak ada wajah yang berhasil diproses dari semua gambar.")
        return False
             
    for pos in person_imgs: #there r some exceptions here, but I'll just leave it as this to keep it simple
        if person_imgs[pos]:  # PERBAIKAN: Cek person_imgs bukan person_features
            print(f"Extracting features for position: {pos}")
            features = extract_feature.get_features(person_imgs[pos])
            person_features[pos] = [np.mean(features, axis=0).tolist()]
        
    face_vector = []
    if person_features.get("Center"):
        face_vector = person_features["Center"][0]
        print("Using Center position features")
    elif person_features.get("Left"):
        face_vector = person_features["Left"][0]
        print("Using Left position features")
    elif person_features.get("Right"):
        face_vector = person_features["Right"][0]
        print("Using Right position features")

    if not face_vector:
        print("Gagal ekstrak fitur wajah dari semua posisi.")
        return False

    print(f"Face vector extracted, length: {len(face_vector)}")
    return face_vector


def add_face_local(image_paths_list):
    import json
    import cv2
    import numpy as np
    
    FRGraph = FaceRecGraph()
    MTCNNGraph = FaceRecGraph()
    aligner = AlignCustom()
    extract_feature = FaceFeature(FRGraph)
    face_detect = MTCNNDetect(MTCNNGraph, scale_factor=2) 

    person_imgs = {"Left" : [], "Right": [], "Center": []}
    person_features = {"Left" : [], "Right": [], "Center": []}
    no = 0
    
    for image_path in image_paths_list:
        no += 1
        print(f"Processing image {no}: {image_path}")

        try:
            # Baca langsung dari file path lokal
            frame = cv2.imread(image_path)
            if frame is None:
                print(f"Gagal baca file: {image_path}")
                continue

            # ✅ TAMBAH DEBUG INI:
            height, width = frame.shape[:2]
            print(f"📊 Image size: {width}x{height}")
            print(f"📊 Image channels: {frame.shape[2] if len(frame.shape) > 2 else 1}")
            
            # Cek brightness
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            avg_brightness = gray.mean()
            print(f"📊 Average brightness: {avg_brightness:.1f}")
            
            # Cek apakah gambar terlalu gelap/terang
            if avg_brightness < 50:
                print("⚠️ Gambar terlalu gelap")
            elif avg_brightness > 200:
                print("⚠️ Gambar terlalu terang")
                
                
        except Exception as e:
            print(f"Error membaca {image_path}:", e)
            continue

        try:
            print("Getting landmark...")
            rects, landmarks = face_detect.detect_face(frame, 40)
        except Exception as e:
            print("Gagal deteksi wajah:", e)
            continue
        
        if(len(rects)==0):
            print("Tidak ada wajah terdeteksi.")
            continue
        
        for (i, rect) in enumerate(rects):
            aligned_frame, pos = aligner.align(160,frame,landmarks[:,i])
            if len(aligned_frame) == 160 and len(aligned_frame[0]) == 160:
                person_imgs[pos].append(aligned_frame)
    
    # Sisa kode sama dengan function asli...
    total_images = sum(len(person_imgs[pos]) for pos in person_imgs)
    if total_images == 0:
        print("Tidak ada wajah yang berhasil diproses.")
        return False
             
    for pos in person_imgs:
        if person_imgs[pos]:
            print(f"Extracting features for position: {pos}")
            features = extract_feature.get_features(person_imgs[pos])
            person_features[pos] = [np.mean(features, axis=0).tolist()]
        
    face_vector = []
    if person_features.get("Center"):
        face_vector = person_features["Center"][0]
    elif person_features.get("Left"):
        face_vector = person_features["Left"][0]
    elif person_features.get("Right"):
        face_vector = person_features["Right"][0]

    if not face_vector:
        print("Gagal ekstrak fitur wajah.")
        return False

    print(f"Face vector extracted, length: {len(face_vector)}")
    return face_vector


# ========================================
# RLE FUNCTIONS - TAMBAH DI AKHIR main.py
# ========================================

def verify_face_rle(url_image, id_pegawai):
    """
    Verify face untuk RLE - TERPISAH dari verify_face yang existing
    """
    import time
    import cv2
    import numpy as np
    from urllib.request import urlopen
    
    FRGraph = FaceRecGraph()
    MTCNNGraph = FaceRecGraph()
    aligner = AlignCustom()
    extract_feature = FaceFeature(FRGraph)
    face_detect = MTCNNDetect(MTCNNGraph, scale_factor=2) 
    
    detect_time = time.time()
    print(f"🔍 RLE Face verification for: {id_pegawai}")
    print(f"🖼️ RLE Image URL: {url_image}")
    
    # Download dan decode gambar
    try:
        req = urlopen(url_image)
        arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
        frame = cv2.imdecode(arr, -1)
        
        if frame is None:
            print("❌ RLE Failed to decode image")
            return False
            
    except Exception as e:
        print(f"❌ RLE Error downloading image: {e}")
        return False
    
    try:
        rects, landmarks = face_detect.detect_face(frame, 80)
        print(f"✅ RLE Detected {len(rects)} faces")
    except Exception as e:
        print(f"❌ RLE Face detection failed: {e}")
        return False
        
    aligns = []
    positions = []

    for (i, rect) in enumerate(rects):
        aligned_face, face_pos = aligner.align(160, frame, landmarks[:, i])
        if len(aligned_face) == 160 and len(aligned_face[0]) == 160:
            aligns.append(aligned_face)
            positions.append(face_pos)
            print(f"✅ RLE Face {i+1} aligned successfully")
        else: 
            print(f"❌ RLE Face {i+1} alignment failed")
            
    if len(aligns) > 0:
        print(f"🔄 RLE Extracting features from {len(aligns)} aligned faces...")
        features_arr = extract_feature.get_features(aligns)
        
        # ✅ PANGGIL findPeople_rle (FUNCTION BARU)
        recog_data = findPeople_rle(features_arr, positions, id_pegawai)
        
        detect_total_time = time.time() - detect_time
        print(f"⏱️ RLE Total verification time: {detect_total_time:.3f}s")
        
        return recog_data
    else:
        print("❌ RLE No faces could be aligned")
        return False


def findPeople_rle(features_arr, positions, id_pegawai, thres=0.6, percent_thres=70):
    """
    FindPeople untuk RLE - TERPISAH dari findPeople yang existing
    Query ke KompresiRLE table instead of KompresiHuffman
    """
    print(f"🔍 Looking for RLE biometrik data for: {id_pegawai}")
    try:
        import sys
        import numpy as np
        import json
        from sipreti.models import KompresiRLE  # ← IMPORT MODEL RLE
        
        # ✅ CARI DI RLE TABLE (BUKAN HUFFMAN)
        rle_records = KompresiRLE.objects.filter(id_pegawai=str(id_pegawai))
        
        if rle_records.count() == 0:
            print("Employee not found in KompresiRLE")
            return False
        
        print(f"✅ Found {rle_records.count()} RLE records")
        
        # Ambil record terbaru
        latest_record = rle_records.order_by('-id').first()
        
        if not latest_record.face_vector:
            print("No face vector stored in latest RLE record")
            return False
        
        # ✅ PARSE FACE VECTOR DATA (SAMA SEPERTI HUFFMAN)
        face_vector_data = json.loads(latest_record.face_vector)
        
        if isinstance(face_vector_data, dict) and "Center" in face_vector_data:
            # Format: {"Center": [[vector1], [vector2], ...]}
            center_vectors = face_vector_data["Center"]
            print(f"✅ Found RLE Center data with {len(center_vectors)} vectors")
        elif isinstance(face_vector_data, list) and len(face_vector_data) == 128:
            # Format: langsung array [128D]
            center_vectors = [face_vector_data]  # Wrap dalam array
            print("✅ Single RLE vector converted to Center format")
        else:
            print(f"❌ Invalid RLE face vector format: {type(face_vector_data)}")
            return False
        
    except json.JSONDecodeError as je:
        print(f"Invalid JSON format in RLE face_vector: {je}")
        return False
    except Exception as e:
        print(f"KompresiRLE error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ✅ PROSES EUCLIDEAN DISTANCE (SAMA SEPERTI HUFFMAN)
    print(f"🔄 Starting RLE comparison for {len(features_arr)} faces")

    for (i, features_128D) in enumerate(features_arr):
        smallest = sys.maxsize
        print(f"🔄 Processing RLE face #{i+1}")
        
        for j, stored_vector in enumerate(center_vectors):
            # ✅ HITUNG EUCLIDEAN DISTANCE
            distance = np.sqrt(np.sum(np.square(np.array(stored_vector) - np.array(features_128D))))
            print(f"   RLE Distance to stored vector {j+1}: {distance:.4f}")
            
            if distance < smallest:
                smallest = distance
                print(f"   ✅ RLE New best distance: {smallest:.4f}")

        if smallest <= thres:  # Jika distance <= 0.6 (threshold)
            percentage = max(0, 100 * (1 - (smallest / thres)))
        else:
            percentage = 0
            
        print(f"📊 RLE Best distance: {smallest:.4f}")
        print(f"📊 RLE Percentage: {percentage:.2f}%")
        print(f"📊 RLE Threshold: {percent_thres}%")

        if percentage <= percent_thres:
            print(f"❌ RLE WAJAH TIDAK MIRIP: {percentage:.2f}% <= {percent_thres}%")
            return False
        else:
            print(f"✅ RLE WAJAH MIRIP: {percentage:.2f}% > {percent_thres}%")
            
    print("✅ Semua wajah RLE yang terdeteksi mirip dengan data tersimpan!")
    return True



def verify_face_arithmetic(url_image, id_pegawai):
    """
    Verify face menggunakan data dari KompresiArithmetic
    """
    from sipreti.face_recognition.main import FaceRecGraph, AlignCustom, FaceFeature, MTCNNDetect
    import time
    import cv2
    import numpy as np
    from urllib.request import urlopen

    FRGraph = FaceRecGraph()
    MTCNNGraph = FaceRecGraph()
    aligner = AlignCustom()
    extract_feature = FaceFeature(FRGraph)
    face_detect = MTCNNDetect(MTCNNGraph, scale_factor=2) 
    
    detect_time = time.time()
    req = urlopen(url_image)
    arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
    frame = cv2.imdecode(arr, -1)
    
    try:
        rects, landmarks = face_detect.detect_face(frame, 80)
    except:
        print("❌ Gagal detect face arithmetic")
        return False
    
    aligns = []
    positions = []

    for (i, rect) in enumerate(rects):
        aligned_face, face_pos = aligner.align(160, frame, landmarks[:,i])
        if len(aligned_face) == 160 and len(aligned_face[0]) == 160:
            aligns.append(aligned_face)
            positions.append(face_pos)
        else: 
            print("❌ Align face arithmetic failed")
    
    if(len(aligns) > 0):
        features_arr = extract_feature.get_features(aligns)
        recog_data = findPeople_arithmetic(features_arr, positions, id_pegawai)
        return recog_data
    
    return False


# ✅ 5. FindPeople untuk Arithmetic (cari di table KompresiArithmetic)
def findPeople_arithmetic(features_arr, positions, id_pegawai, thres=0.6, percent_thres=70):
    """
    Find people menggunakan data dari KompresiArithmetic
    """
    print(f"🔍 Looking for arithmetic biometrik data for: {id_pegawai}")
    try:
        import sys
        import numpy as np
        import json
        from sipreti.models import KompresiArithmetic
        
        # Cari di KompresiArithmetic table
        arithmetic_records = KompresiArithmetic.objects.filter(id_pegawai=str(id_pegawai))
        
        if arithmetic_records.count() == 0:
            print("❌ Employee not found in KompresiArithmetic")
            return False
        
        print(f"✅ Found {arithmetic_records.count()} arithmetic records")
        
        # Ambil record terbaru
        latest_record = arithmetic_records.order_by('-id').first()
        
        if not latest_record.face_vector:
            print("❌ No face vector stored in latest arithmetic record")
            return False
        
        # Parse face vector data
        face_vector_data = json.loads(latest_record.face_vector)
        
        if isinstance(face_vector_data, dict) and "Center" in face_vector_data:
            center_vectors = face_vector_data["Center"]
            print(f"✅ Found arithmetic Center data with {len(center_vectors)} vectors")
        elif isinstance(face_vector_data, list) and len(face_vector_data) == 128:
            center_vectors = [face_vector_data]
            print("✅ Single arithmetic vector converted to Center format")
        else:
            print(f"❌ Invalid arithmetic face vector format: {type(face_vector_data)}")
            return False
        
    except json.JSONDecodeError as je:
        print(f"❌ Invalid JSON format in arithmetic face_vector: {je}")
        return False
    except Exception as e:
        print(f"❌ KompresiArithmetic error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Proses comparison
    print(f"🔄 Starting arithmetic comparison for {len(features_arr)} faces")

    for (i, features_128D) in enumerate(features_arr):
        smallest = sys.maxsize
        print(f"🔄 Processing arithmetic face #{i+1}")
        
        for j, stored_vector in enumerate(center_vectors):
            distance = np.sqrt(np.sum(np.square(np.array(stored_vector) - np.array(features_128D))))
            print(f"   Arithmetic distance to stored vector {j+1}: {distance:.4f}")
            
            if distance < smallest:
                smallest = distance
                print(f"   ✅ New best arithmetic distance: {smallest:.4f}")

        if smallest <= thres:
            percentage = max(0, 100 * (1 - (smallest / thres)))
        else:
            percentage = 0
            
        print(f"📊 Best arithmetic distance: {smallest:.4f}")
        print(f"📊 Arithmetic percentage: {percentage:.2f}%")
        print(f"📊 Threshold: {percent_thres}%")

        if percentage <= percent_thres:
            print(f"❌ ARITHMETIC WAJAH TIDAK MIRIP: {percentage:.2f}% <= {percent_thres}%")
            return False
        else:
            print(f"✅ ARITHMETIC WAJAH MIRIP: {percentage:.2f}% > {percent_thres}%")
            
    print("✅ Semua wajah arithmetic yang terdeteksi mirip dengan data tersimpan!")
    return True
