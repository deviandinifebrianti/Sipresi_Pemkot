<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Detail Jabatan - SI Preti</title>
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
      margin-left: auto; /* Penting: ini membuat menu berada di kanan */
    }
    
    .nav-link {
      color: white;
      text-decoration: none;
      padding: 10px 15px;
      margin: 0 2px;
      font-size: 0.9rem;
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
    
    .content-header {
      background-color: #4CAF50;
      color: white;
      padding: 12px 15px;
      margin-bottom: 20px;
    }
    
    .content-header h2 {
      font-size: 22px;
      margin: 0;
      font-weight: 600;
    }
    
    /* Responsive adjustments */
    @media (max-width: 768px) {
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
    
    .detail-container {
      width: 100%;
      max-width: 600px;
      background-color: white;
      border-radius: 5px;
      box-shadow: 0 2px 5px rgba(0,0,0,0.1);
      overflow: hidden;
      margin: 30px auto;
    }
    
    .detail-header {
      background-color: #4CAF50;
      color: white;
      padding: 12px 15px;
      font-size: 18px;
      font-weight: 600;
    }
    
    .detail-body {
      padding: 20px;
    }
    
    .table {
      width: 100%;
      margin-bottom: 0;
    }
    
    .table tr td:first-child {
      width: 30%;
      font-weight: 500;
      background-color: #f9f9f9;
    }
    
    .table tr:last-child td {
      border-bottom: none;
      padding-top: 20px;
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
    
    /* Responsive adjustments */
    @media (max-width: 768px) {
      .detail-container {
        margin: 15px;
        max-width: 100%;
      }
    }
  </style>
</head>
<body>
  <!-- Header dengan Navbar tanpa ul li -->
  <nav class="navbar">
    <a href="<?php echo site_url('welcome'); ?>" class="navbar-brand">
      <img src="<?= base_url('assets/datatables/images/logo.jpg') ?>" alt="Logo"> Sipreti
    </a>
    
    <button class="navbar-toggler" onclick="toggleMenu()">☰</button>
    
    <div class="navbar-menu" id="navbarMenu">
      <a href="<?php echo site_url('welcome'); ?>" class="nav-link">Dashboard</a>
      <a href="<?php echo site_url('pegawai'); ?>" class="nav-link">Pegawai</a>
      <a href="<?php echo site_url('jabatan'); ?>" class="nav-link">Jabatan</a>
      <a href="<?php echo site_url('radius_absen'); ?>" class="nav-link">Radius Absen</a>
      <a href="<?php echo site_url('log_absensi'); ?>" class="nav-link">Log Absensi</a>
      <a href="<?php echo site_url('unit_kerja'); ?>" class="nav-link">Unit Kerja</a>
      <a href="<?php echo site_url('user_android'); ?>" class="nav-link">User Android</a>
    </div>
  </nav>

  <!-- Content Header -->
  

  <div class="detail-container">
    <div class="detail-header">
      Detail Jabatan
    </div>
    
    <div class="detail-body">
      <table class="table table-bordered">
        <tr>
          <td>Nama Jabatan</td>
          <td><?php echo $nama_jabatan; ?></td>
        </tr>
        <tr>
          <td>Created At</td>
          <td><?php echo $created_at; ?></td>
        </tr>
        <tr>
          <td>Updated At</td>
          <td><?php echo $updated_at; ?></td>
        </tr>
        <tr>
          <td>Deleted At</td>
          <td><?php echo $deleted_at; ?></td>
        </tr>
        <tr>
          <td></td>
          <td>
            <a href="<?php echo site_url('jabatan') ?>" class="btn btn-default">Kembali</a>
            <a href="<?php echo site_url('jabatan/update/'.$id_jabatan) ?>" class="btn btn-primary">Edit</a>
          </td>
        </tr>
      </table>
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