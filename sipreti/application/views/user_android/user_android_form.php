<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Form User Android - SI Preti</title>
  <link rel="stylesheet" href="<?php echo base_url('assets/bootstrap/css/bootstrap.min.css') ?>"/>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.0/font/bootstrap-icons.css">
  <style>
    body {
      font-family: Arial, sans-serif;
      margin: 0;
      padding: 0;
      background-color: #e0e0e0;
    }
    
    /* Header navbar styling tanpa ul li */
    .navbar {
      background-color: #4B0082;
      padding: 10px 20px;
      display: flex;
      align-items: center;
    }
    
    .navbar-brand {
      display: flex;
      align-items: center;
      color: white;
      font-weight: bold;
      font-size: 18px;
      margin-right: 20px;
      text-decoration: none;
    }
    
    .navbar-brand img {
      height: 30px;
      margin-right: 10px;
    }
    
    .navbar-menu {
      display: flex;
      align-items: center;
      margin-left: auto;
    }
    
    .nav-link {
      color: white;
      text-decoration: none;
      padding: 10px 15px;
      margin: 0 2px;
      font-size: 15px;
      display: inline-block;
      transition: background-color 0.3s;
    }
    
    .nav-link:hover {
      background-color: rgba(255, 255, 255, 0.1);
      border-radius: 4px;
    }
    
    .navbar-toggler {
      display: none;
      background: none;
      border: none;
      color: white;
      font-size: 24px;
      cursor: pointer;
    }
    
    /* Form styling */
    .form-container {
      width: 100%;
      max-width: 800px; /* ✅ EXPANDED untuk device info */
      background-color: white;
      border-radius: 5px;
      box-shadow: 0 2px 5px rgba(0,0,0,0.1);
      overflow: hidden;
      margin: 30px auto;
    }
    
    .form-header {
      background-color: #4CAF50;
      color: white;
      padding: 12px 15px;
      font-size: 18px;
      font-weight: 600;
    }
    
    /* ✅ SECTION HEADERS seperti di read page */
    .section-header {
      background-color: #f8f9fa;
      color: #495057;
      padding: 10px 15px;
      font-size: 16px;
      font-weight: 600;
      border-bottom: 1px solid #dee2e6;
      margin: 0 -20px 15px -20px;
    }
    
    .section-header i {
      margin-right: 8px;
    }
    
    .form-body {
      padding: 20px;
    }
    
    .form-group {
      margin-bottom: 15px;
    }
    
    .form-label {
      display: block;
      margin-bottom: 5px;
      font-weight: 500;
      font-size: 14px;
      color: #495057;
    }
    
    .form-control {
      width: 100%;
      padding: 8px 12px;
      border: 1px solid #ddd;
      border-radius: 4px;
      font-size: 14px;
    }
    
    .form-control:focus {
      outline: none;
      border-color: #4CAF50;
      box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
    }
    
    /* ✅ SPECIAL STYLING untuk device fields */
    .device-section .form-control {
      background-color: #f8fffe;
      border-color: #17a2b8;
    }
    
    .device-section .form-control:focus {
      border-color: #17a2b8;
      box-shadow: 0 0 0 2px rgba(23, 162, 184, 0.2);
    }
    
    .error-text {
      color: #dc3545;
      font-size: 12px;
      margin-top: 3px;
    }
    
    .form-actions {
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      margin-top: 20px;
    }
    
    .btn {
      padding: 8px 20px;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-weight: 500;
      font-size: 14px;
    }
    
    .btn-default {
      background-color: #f5f5f5;
      color: #333;
    }
    
    .btn-primary {
      background-color: #9C27B0;
      color: white;
    }
    
    /* Two column layout for form fields */
    @media (min-width: 768px) {
      .form-row {
        display: flex;
        margin-left: -10px;
        margin-right: -10px;
      }
      
      .form-col {
        flex: 1;
        padding-left: 10px;
        padding-right: 10px;
      }
      
      /* ✅ THREE COLUMN LAYOUT untuk device info */
      .form-row-3 {
        display: flex;
        margin-left: -8px;
        margin-right: -8px;
      }
      
      .form-col-3 {
        flex: 1;
        padding-left: 8px;
        padding-right: 8px;
      }
    }
    
    /* Responsive adjustments */
    @media (max-width: 768px) {
      .form-container {
        margin: 15px;
        max-width: 100%;
      }
      
      .section-header {
        margin: 0 -15px 15px -15px;
      }
      
      .form-body {
        padding: 15px;
      }
      
      .navbar {
        flex-wrap: wrap;
      }
      
      .navbar-menu {
        display: none;
        width: 100%;
        flex-direction: column;
        align-items: flex-start;
        margin-top: 10px;
      }
      
      .navbar-menu.active {
        display: flex;
      }
      
      .nav-link {
        width: 100%;
        margin: 2px 0;
      }
      
      .navbar-toggler {
        display: block;
        margin-left: auto;
      }
    }
  </style>
</head>
<body>
  <!-- Header dengan Navbar tanpa ul li -->
  <nav class="navbar">
    <a href="<?php echo site_url('welcome'); ?>" class="navbar-brand">
      <img src="<?= base_url('assets/datatables/images/logo.jpg') ?>" alt="SI Preti Logo"> SI Preti
    </a>
    
    <button class="navbar-toggler" onclick="toggleMenu()">☰</button>
    
    <div class="navbar-menu" id="navbarMenu">
      <a href="<?php echo site_url('welcome'); ?>" class="nav-link">Dashboard</a>
      <a href="<?php echo site_url('log_absensi'); ?>" class="nav-link">Log Absensi</a>
      <a href="<?php echo site_url('pegawai'); ?>" class="nav-link">Pegawai</a>
      <a href="<?php echo site_url('user_android'); ?>" class="nav-link">User Android</a>
      <a href="<?php echo site_url('vektor_pegawai'); ?>" class="nav-link">Vektor Pegawai</a>
    </div>
  </nav>

  <div class="form-container">
    <div class="form-header">
      User Android <?php echo $button ?>
    </div>
    
    <div class="form-body">
      <form action="<?php echo $action; ?>" method="post">
        
        <!-- ✅ SECTION 1: USER INFORMATION -->
        <div class="section-header">
          <i class="bi bi-person-circle"></i>Informasi User
        </div>
        
        <div class="form-row">
          <div class="form-col">
            <div class="form-group">
              <label for="id_pegawai" class="form-label">ID Pegawai <?php echo form_error('id_pegawai') ?></label>
              <input type="text" class="form-control" name="id_pegawai" id="id_pegawai" placeholder="ID Pegawai" value="<?php echo $id_pegawai; ?>" />
            </div>
          </div>
          
          <div class="form-col">
            <div class="form-group">
              <label for="username" class="form-label">Username <?php echo form_error('username') ?></label>
              <input type="text" class="form-control" name="username" id="username" placeholder="Username" value="<?php echo $username; ?>" />
            </div>
          </div>
        </div>
        
        <!-- ✅ TIMESTAMP FIELDS (Read-only untuk update, hidden untuk create) -->
        <?php if ($button == 'Update'): ?>
        <div class="form-row">
          <div class="form-col">
            <div class="form-group">
              <label for="created_at" class="form-label">Created At</label>
              <input type="text" class="form-control" name="created_at" id="created_at" readonly value="<?php echo isset($created_at) ? $created_at : ''; ?>" />
            </div>
          </div>
          
          <div class="form-col">
            <div class="form-group">
              <label for="updated_at" class="form-label">Updated At</label>
              <input type="text" class="form-control" name="updated_at" id="updated_at" readonly value="<?php echo isset($updated_at) ? $updated_at : ''; ?>" />
            </div>
          </div>
        </div>
        
        <div class="form-row">
          <div class="form-col">
            <div class="form-group">
              <label for="deleted_at" class="form-label">Deleted At</label>
              <input type="text" class="form-control" name="deleted_at" id="deleted_at" placeholder="Kosong jika aktif" value="<?php echo isset($deleted_at) ? $deleted_at : ''; ?>" />
            </div>
          </div>
          
          <div class="form-col">
            <div class="form-group">
              <label for="last_login" class="form-label">Last Login</label>
              <input type="text" class="form-control" name="last_login" id="last_login" readonly value="<?php echo isset($last_login) ? $last_login : ''; ?>" />
            </div>
          </div>
        </div>
        <?php endif; ?>
        
        <!-- ✅ SECTION 2: DEVICE INFORMATION -->
        <div class="section-header" style="margin-top: 30px;">
          <i class="bi bi-phone"></i>Informasi Device
        </div>
        
        <div class="device-section">
          <div class="form-group">
            <label for="device_id" class="form-label">Device ID <?php echo form_error('device_id') ?></label>
            <input type="text" class="form-control" name="device_id" id="device_id" placeholder="Device ID (Build ID)" value="<?php echo isset($device_id) ? $device_id : ''; ?>" />
          </div>
          
          <div class="form-row-3">
            <div class="form-col-3">
              <div class="form-group">
                <label for="device_brand" class="form-label">Brand <?php echo form_error('device_brand') ?></label>
                <input type="text" class="form-control" name="device_brand" id="device_brand" placeholder="Brand (e.g., Samsung, Xiaomi)" value="<?php echo isset($device_brand) ? $device_brand : ''; ?>" />
              </div>
            </div>
            
            <div class="form-col-3">
              <div class="form-group">
                <label for="device_model" class="form-label">Model <?php echo form_error('device_model') ?></label>
                <input type="text" class="form-control" name="device_model" id="device_model" placeholder="Model (e.g., SM-A325F)" value="<?php echo isset($device_model) ? $device_model : ''; ?>" />
              </div>
            </div>
            
            <div class="form-col-3">
              <div class="form-group">
                <label for="device_os_version" class="form-label">OS Version <?php echo form_error('device_os_version') ?></label>
                <input type="text" class="form-control" name="device_os_version" id="device_os_version" placeholder="OS Version (e.g., 14)" value="<?php echo isset($device_os_version) ? $device_os_version : ''; ?>" />
              </div>
            </div>
          </div>
          
          <div class="form-group">
            <label for="device_sdk_version" class="form-label">SDK Version (API Level) <?php echo form_error('device_sdk_version') ?></label>
            <input type="number" class="form-control" name="device_sdk_version" id="device_sdk_version" placeholder="SDK Version (e.g., 34)" value="<?php echo isset($device_sdk_version) ? $device_sdk_version : ''; ?>" />
          </div>
        </div>
        
        <input type="hidden" name="id_user_android" value="<?php echo $id_user_android; ?>" /> 
        
        <div class="form-actions">
          <a href="<?php echo site_url('user_android') ?>" class="btn btn-default">Cancel</a>
          <button type="submit" class="btn btn-primary"><?php echo $button ?></button>
        </div>
      </form>
    </div>
  </div>

  <!-- Bootstrap JS -->
  <script src="<?php echo base_url('assets/js/jquery.min.js') ?>"></script>
  <script src="<?php echo base_url('assets/bootstrap/js/bootstrap.min.js') ?>"></script>
  
  <!-- Script untuk toggle menu pada mobile -->
  <script>
  function toggleMenu() {
    var menu = document.getElementById('navbarMenu');
    menu.classList.toggle('active');
  }
  </script>
</body>
</html>