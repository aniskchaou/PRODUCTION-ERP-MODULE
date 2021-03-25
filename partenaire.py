# -*- coding: utf-8 -*-

import sys
import openerp
from openerp import models, fields, api, _
from openerp import tools
from datetime import date
from datetime import datetime
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
import re
import base64
from openerp.exceptions import except_orm, Warning, RedirectWarning

#----------------------------------------------------------
# achat_fournisseur
#----------------------------------------------------------
class achat_fournisseur(models.Model):

	@api.multi
	def name_get(self):
		result = []
		for record in self:
			result.append((record.id, record.code_fournisseur + ' : ' + record.nom)) 
		return result

	@api.one
	def _get_commande_count(self):
		for fournisseur in self:
			self.commande_count  = self.env['commande.fournisseur'].search_count([('fournisseur_id', '=', fournisseur.id)])


	_name = 'achat.fournisseur'

	image = fields.Binary("Image")
	image_medium = fields.Binary("Medium-sized image", compute='_compute_images', inverse='_inverse_image_medium', store=True)
	image_small = fields.Binary("Small-sized image", compute='_compute_images', inverse='_inverse_image_small', store=True)
	code_fournisseur = fields.Char('Code fournisseur :', required=True)
	nom = fields.Char('Nom', required=True)
	adresse = fields.Char('Adresse')
	code_tva = fields.Char('Code TVA')
	tel = fields.Char('Téléphone')
	fax = fields.Char('Fax')
	email = fields.Char('Email')
	responsable = fields.Char('Responsable')
	active = fields.Boolean('Actif', default=True)
	commande_count = fields.Integer(compute='_get_commande_count', string='Commandes')

	@api.model
	def create(self, values):
		#test code_fournisseur doit etre unique
		self.env.cr.execute('select * from achat_fournisseur where code_fournisseur = %s',(values['code_fournisseur'],))
		lines = self.env.cr.dictfetchall()
		if lines:
			raise Warning(_('Erreur!'), 
						_('Code fournisseur existe déjà [ %s ].')% (values['code_fournisseur']))
		return super(achat_fournisseur, self).create(values)

	@api.multi
	def write(self, values):
		obj_id=super(achat_fournisseur,self).write(values)
		for obj in self:
			self.env.cr.execute('select * from achat_fournisseur where code_fournisseur = %s',(obj.code_fournisseur,))
			lines = self.env.cr.dictfetchall()
			if len(lines) > 1:
				raise Warning(_('Erreur!'), 
							_('Code fournisseur existe déjà [ %s ].')% (obj.code_fournisseur))
		return obj_id

	@api.depends('image')
	def _compute_images(self):
		for rec in self:
			rec.image_medium = tools.image_resize_image_medium(rec.image)
			rec.image_small = tools.image_resize_image_small(rec.image)

	def _inverse_image_medium(self):
		for rec in self:
			rec.image = tools.image_resize_image_big(rec.image_medium)

	def _inverse_image_small(self):
		for rec in self:
			rec.image = tools.image_resize_image_big(rec.image_small)

	@api.multi
	def commande_fournisseur(self):
		return { 
				'name': _("Commande fournisseur"),
				'type': 'ir.actions.act_window',
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'commande.fournisseur',
				'view_id': False,
				'context': {'default_fournisseur_id': self.id},
				}

#----------------------------------------------------------
# vente_client
#----------------------------------------------------------
class vente_client(models.Model):

	@api.multi
	def name_get(self):
		result = []
		for record in self:
			result.append((record.id, record.code_client + ' : ' + record.nom)) 
		return result

	@api.model
	def _get_default_value(self):
		"""
			Taux TVA par défaut
		"""
		taux_tva_obj = self.env['taux.tva'] 
		taux_tva = taux_tva_obj.search([('default','=',True)], limit=1)
		if taux_tva:
			return taux_tva[0].id
		return False

	@api.one
	def _get_commande_count(self):
		for client in self:
			self.commande_count  = self.env['production.commande'].search_count([('client_id', '=', client.id)])


	_name = 'vente.client'

	image = fields.Binary("Image")
	image_medium = fields.Binary("Medium-sized image", compute='_compute_images', inverse='_inverse_image_medium', store=True)
	image_small = fields.Binary("Small-sized image", compute='_compute_images', inverse='_inverse_image_small', store=True)
	code_client = fields.Char('Code client :', required=True)
	nom = fields.Char('Nom', required=True)
	adresse = fields.Char('Adresse')
	code_tva = fields.Char('Code TVA')
	tel = fields.Char('Téléphone')
	fax = fields.Char('Fax')
	email = fields.Char('Email')
	responsable = fields.Char('Responsable')
	taux_tva_id = fields.Many2one('taux.tva', 'Taux TVA', required=True, ondelete='cascade', default=_get_default_value)

	commande_count = fields.Integer(compute='_get_commande_count', string='Commandes')

	@api.model
	def create(self, values):
		#test code_client doit etre unique
		self.env.cr.execute('select * from vente_client where code_client = %s', (values['code_client'],))
		lines = self.env.cr.dictfetchall()
		if lines:
			raise Warning(_('Erreur!'), 
						_('Code client existe déjà [ %s ].')% (values['code_client']))
		return super(vente_client, self).create(values)

	@api.multi
	def write(self, values):
		obj_id=super(vente_client,self).write(values)
		for obj in self:
			self.env.cr.execute('select * from vente_client where code_client = %s', (obj.code_client,))
			lines = self.env.cr.dictfetchall()
			if len(lines) > 1:
				raise Warning(_('Erreur!'), 
							_('Code client existe déjà [ %s ].')% (obj.code_client))
		return obj_id

	@api.depends('image')
	def _compute_images(self):
		for rec in self:
			rec.image_medium = tools.image_resize_image_medium(rec.image)
			rec.image_small = tools.image_resize_image_small(rec.image)

	def _inverse_image_medium(self):
		for rec in self:
			rec.image = tools.image_resize_image_big(rec.image_medium)

	def _inverse_image_small(self):
		for rec in self:
			rec.image = tools.image_resize_image_big(rec.image_small)

	@api.multi
	def commande_client(self):
		return { 
				'name': _("Commande client"),
				'type': 'ir.actions.act_window',
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'production.commande',
				'view_id': False,
				'context': {'default_client_id': self.id},
				}
