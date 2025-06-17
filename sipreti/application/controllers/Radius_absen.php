<?php

if (!defined('BASEPATH'))
	exit('No direct script access allowed');

class Radius_absen extends CI_Controller
{
	function __construct()
	{
		parent::__construct();
		$this->load->model('Radius_absen_model');
		$this->load->library('form_validation');
		$this->load->helper('url');
	}

	public function get_detail_json($id)
{
    $data = $this->Radius_absen_model->get_by_id($id);
        if ($row) {
			$data = [
				'alamat' => $row->alamat,
				'latitude' => $row->latitude,
				'longitude' => $row->longitude
			];
			echo json_encode($data);
        } else {
            echo json_encode([]);
        }
}

	public function index()
	{
		$q = urldecode($this->input->get('q', TRUE));
		$start = intval($this->input->get('start'));

		if ($q <> '') {
			$config['base_url'] = base_url() . 'radius_absen/index.html?q=' . urlencode($q);
			$config['first_url'] = base_url() . 'radius_absen/index.html?q=' . urlencode($q);
		} else {
			$config['base_url'] = base_url() . 'radius_absen/index.html';
			$config['first_url'] = base_url() . 'radius_absen/index.html';
		}

		$config['per_page'] = 10;
		$config['page_query_string'] = TRUE;
		$config['total_rows'] = $this->Radius_absen_model->total_rows($q, TRUE);
		$radius_absen = $this->Radius_absen_model->get_limit_data($config['per_page'], $start, $q, TRUE);

		$this->load->library('pagination');
		$this->pagination->initialize($config);

		$data = array(
			'radius_absen_data' => $radius_absen,
			'q' => $q,
			'pagination' => $this->pagination->create_links(),
			'total_rows' => $config['total_rows'],
			'start' => $start,
		);
		$this->load->view('radius_absen/radius_absen_list', $data);
	}

	public function read($id)
	{
		$row = $this->Radius_absen_model->get_by_id($id);
		if ($row && empty($row->deleted_at)) {
			$data = array(
				'id_radius' => $row->id_radius,
				'ukuran' => $row->ukuran,
				'satuan' => $row->satuan,
				'created_at' => $row->created_at,
				'updated_at' => $row->updated_at,
				'deleted_at' => $row->deleted_at,
			);
			$this->load->view('radius_absen/radius_absen_read', $data);
		} else {
			$this->session->set_flashdata('message', 'Record Not Found');
			redirect(site_url('radius_absen'));
		}
	}

	public function create()
	{
		$data = array(
			'button' => 'Create',
			'action' => site_url('radius_absen/create_action'),
			'id_radius' => set_value('id_radius'),
			'ukuran' => set_value('ukuran'),
			'satuan' => set_value('satuan'),
			'latitude' => set_value('latitude'),
    		'longitude' => set_value('longitude'),
		);
		$this->load->view('radius_absen/radius_absen_form', $data);
	}

	public function create_action()
	{
		$this->_rules();

		if ($this->form_validation->run() == FALSE) {
			$this->create();
		} else {
			$data = array(
				'ukuran' => $this->input->post('ukuran', TRUE),
				'satuan' => $this->input->post('satuan', TRUE),
				'created_at' => date('Y-m-d H:i:s'),
				'latitude' => $this->input->post('latitude', TRUE),
    			'longitude' => $this->input->post('longitude', TRUE),
				'updated_at' => NULL,
				'deleted_at' => NULL,
			);

			$this->Radius_absen_model->insert($data);
			$this->session->set_flashdata('message', 'Create Record Success');
			redirect(site_url('radius_absen'));
		}
	}

	public function update($id)
	{
		$row = $this->Radius_absen_model->get_by_id($id);

		if ($row) {
			$data = array(
				'button' => 'Update',
				'action' => site_url('radius_absen/update_action'),
				'id_radius' => set_value('id_radius', $row->id_radius),
				'ukuran' => set_value('ukuran', $row->ukuran),
				'satuan' => set_value('satuan', $row->satuan),
				'latitude' => set_value('latitude'),
    			'longitude' => set_value('longitude'),
			);
			$this->load->view('radius_absen/radius_absen_form', $data);
		} else {
			$this->session->set_flashdata('message', 'Record Not Found');
			redirect(site_url('radius_absen'));
		}
	}

	public function update_action()
	{
		$this->_rules();

		if ($this->form_validation->run() == FALSE) {
			$this->update($this->input->post('id_radius', TRUE));
		} else {
			$data = array(
				'ukuran' => $this->input->post('ukuran', TRUE),
				'satuan' => $this->input->post('satuan', TRUE),
				'updated_at' => date('Y-m-d H:i:s'),
				'latitude' => $this->input->post('latitude', TRUE),
    			'longitude' => $this->input->post('longitude', TRUE),
			);

			$this->Radius_absen_model->update($this->input->post('id_radius', TRUE), $data);
			$this->session->set_flashdata('message', 'Update Record Success');
			redirect(site_url('radius_absen'));
		}
	}

	public function delete($id)
	{
		$row = $this->Radius_absen_model->get_by_id($id);

		if ($row) {
			$data = array(
				'deleted_at' => date('Y-m-d H:i:s'),
			);

			$this->Radius_absen_model->update($id, $data);
			$this->session->set_flashdata('message', 'Delete Record Success');
			redirect(site_url('radius_absen'));
		} else {
			$this->session->set_flashdata('message', 'Record Not Found');
			redirect(site_url('radius_absen'));
		}
	}

	public function _rules()
	{
		$this->form_validation->set_rules('ukuran', 'ukuran', 'trim|required');
		$this->form_validation->set_rules('satuan', 'satuan', 'trim|required');

		$this->form_validation->set_rules('id_radius', 'id_radius', 'trim');
		$this->form_validation->set_error_delimiters('<span class="text-danger">', '</span>');
	}

	public function activate($id)
{
    // Nonaktifkan semua radius dulu
    $this->db->update('radius_absen', ['is_active' => 0]);

    // Aktifkan radius yang dipilih
    $this->db->where('id_radius', $id);
    $this->db->update('radius_absen', ['is_active' => 1]);

    $this->session->set_flashdata('message', 'Radius berhasil diaktifkan');
    redirect(site_url('radius_absen'));
}

public function get_data($id)
{
    $radius = $this->Radius_absen_model->get_by_id($id);
    if ($radius) {
        // kamu bisa tambahkan field 'alamat', 'latitude', 'longitude' di tabel radius
        $data = [
            'alamat' => $radius->alamat,
            'latitude' => $radius->latitude,
            'longitude' => $radius->longitude
        ];
        echo json_encode($data);
    } else {
        echo json_encode(['error' => 'Data tidak ditemukan']);
    }
}




}

/* End of file Radius_absen.php */
/* Location: ./application/controllers/Radius_absen.php */
/* Please DO NOT modify this information : */
/* Generated by Harviacode Codeigniter CRUD Generator 2025-03-12 06:13:47 */
/* http://harviacode.com */
