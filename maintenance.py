# -*- coding: utf-8 -*-

import sys
import openerp

from openerp.osv import fields, osv
from openerp import tools
import datetime
from datetime import date
#from datetime import datetime
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
import re
import base64
import time
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning


#----------------------------------------------------------
# machine_piece_rel
#----------------------------------------------------------
class machine_piece_rel(models.Model):
	_name = "machine.piece.rel"

	piece_id = fields.Many2one('maintenance.piece', 'Piéce', ondelete='cascade')
	machine_id = fields.Many2one('production.machine', 'Machine', ondelete='cascade')

#----------------------------------------------------------
# maintenance_piece
#----------------------------------------------------------
class maintenance_piece(models.Model):
	_name = 'maintenance.piece'

	#code : nom
	@api.multi
	@api.depends('code_piece', 'name')
	def name_get(self):
		result = []
		for record in self:
			result.append((record.id, record.code_piece + ' : ' + record.name))
		return result

	@api.one
	def _get_bon_entree_piece_count(self):
		self.bon_entree_piece_count = len(self.bon_entree_piece_ids)

	code_piece = fields.Char('Code', required=True)
	name = fields.Char('Nom', required=True)
	quantite_stock = fields.Float('Quantite stock')  # name, digits
	stock_min = fields.Float('Stock minimum')
	unite = fields.Selection([('kg','kg'),
							  ('U','U'),
							  ('m','m'),
							  ('m2','m²'),
							  ('m3','m³'),
							  ('l','l'),], 'Unité')
	prix = fields.Float('Prix unitaire (DT)')
	bon_entree_piece_ids = fields.One2many('bon.entree.piece', 'piece_id', 'Bon entrée pièce de rechange')
	bon_entree_piece_count = fields.Integer(compute='_get_bon_entree_piece_count', string='B.E. Pièce')


	@api.model
	def create(self, values):
		#test code_piece doit etre unique
		if self.env['maintenance.piece'].search_count([('code_piece', '=', values['code_piece'])]) > 0:
			raise Warning(_('Erreur!'), 
						_('Code piece existe déjà [ %s ].')% (values['code_piece']))

		new_id = super(maintenance_piece, self).create(values)
		return new_id


	@api.multi
	def write(self, values):
		obj_id = super(maintenance_piece, self).write(values)
		#test code_piece doit etre unique
		if self.env['maintenance.piece'].search_count([('code_piece', '=', self.code_piece)]) > 1:
			raise Warning(_('Erreur!'),
						_('Code piece existe déjà [ %s ].')% (self.code_piece))

		return obj_id


	@api.multi
	def ajouter_bon_entree_piece(self):
		return { 
				'name': _("Bon entrée pièce de rechange"),
				'type': 'ir.actions.act_window',
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'bon.entree.piece',
				'view_id': False,
				'context': {'default_piece_id': self.id},
				}

	def notif(self, title, record_name, res_id, model, recepteur):
		mail_vals = {
					'body': '<html>'+title+'</html>',
					'record_name': record_name,
					'res_id': res_id,
					'reply_to': self.env['res.users'].browse(self.env.uid).name,
					'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
					'model': model,
					'type': 'email',
					'email_from': self.env['res.users'].browse(self.env.uid).name,
					'starred': True,
					}
		message = self.env['mail.message'].create(mail_vals)

		mail_notif_vals = {
						'partner_id': self.env['res.users'].browse(recepteur).partner_id.id,
						'message_id': message.id,
						'is_read': False,
						'starred': True,
						}
		self.env['mail.notification'].create(mail_notif_vals)

		return True

	@api.model
	def verifier_stock_piece(self):
		group = self.env['res.groups'].search([('name', '=', 'Groupe production')])
		for piece in self.env['maintenance.piece'].search([]):
			if piece.quantite_stock <= piece.stock_min:
				for user in group.users:
					title = 'Stock piéce de rechange insuffisant'
					record_name = piece.code_piece
					res_id = piece.id
					model = 'maintenance.piece'
					recepteur = user.id
					self.notif(title, record_name, res_id, model, recepteur)

class maintenance_piece_mail(models.Model):
	_name = "maintenance.piece"
	_inherit = ['maintenance.piece','mail.thread']

#----------------------------------------------------------
# bon_entree_piece
#----------------------------------------------------------
class bon_entree_piece(models.Model):
	_name='bon.entree.piece'

	code_bon = fields.Char('Code bon :', readonly=True)
	piece_id = fields.Many2one('maintenance.piece', 'Pièce de rechange', ondelete='cascade', required=True)
	quantite = fields.Float('Quantité', required=True)
	unite = fields.Selection([('kg','kg'),
							  ('U','U'),
							  ('m','m'),
							  ('m2','m²'),
							  ('m3','m³'),
							  ('l','l'),], related='piece_id.unite', readonly=True)
	date = fields.Date('Date', default= lambda *a:datetime.datetime.now().strftime('%Y-%m-%d'), required=True)
	fournisseur_id = fields.Many2one('achat.fournisseur', 'Fournisseur', ondelete='cascade')

	@api.model
	def create(self, values):
		#test si quantite <= 0 on genere exception
		if values['quantite'] <= 0:
			raise Warning(_('Erreur!'), 
						_('La quantité doit étre supérieur strictement à zero ( %s )')% (values['quantite']))

		#generer code sequence "code_bon"
		values['code_bon'] = self.env['ir.sequence'].get('bon.entree.piece')

		#augmenter stock
		for piece in self.env['maintenance.piece'].browse(values['piece_id']):
			piece.quantite_stock += values['quantite']

		new_id = super(bon_entree_piece, self).create(values)
		return new_id

	@api.multi
	def write(self, values):
		nouv_quantite = values.get('quantite', None)
		nouv_piece_id = values.get('piece_id', None)
		ancien_piece_obj = self.env['maintenance.piece'].browse(self.piece_id.id)

		#test si quantite <= 0 on genere exception
		if nouv_quantite:
			if nouv_quantite <= 0:
				raise Warning(_('Erreur!'), 
							_('La quantité doit étre supérieur strictement à zero ( %s )')% (nouv_quantite))

		#modifier stock
		if nouv_piece_id:
			nouv_piece_obj = self.env['maintenance.piece'].browse(nouv_piece_id)
			if nouv_quantite:
				ancien_piece_obj.quantite_stock -= self.quantite
				nouv_piece_obj.quantite_stock += nouv_quantite
			else:#quantite non changer
				ancien_piece_obj.quantite_stock -= self.quantite
				nouv_piece_obj.quantite_stock += self.quantite
		else:#piece non changer
			if nouv_quantite:
				ancien_piece_obj.quantite_stock -= self.quantite
				ancien_piece_obj.quantite_stock += nouv_quantite

		obj_id=super(bon_entree_piece, self).write(values)

		return obj_id

	@api.multi
	def unlink(self):
		for rec in self:
			#retirer la quantite du stock
			piece_obj = self.env['maintenance.piece'].browse(rec.piece_id.id)
			piece_obj.quantite_stock -= rec.quantite

		return super(bon_entree_piece, self).unlink()

#----------------------------------------------------------
# maintenance_panne
#----------------------------------------------------------
class maintenance_panne(models.Model):
	_name = 'maintenance.panne'
	_order = "occurrence_panne"

	@api.one
	@api.depends('demande_intervention_ids')
	def _get_occurrence_panne(self):
		self.occurrence_panne = len(self.demande_intervention_ids)

	@api.one
	@api.depends('demande_intervention_ids')
	def _get_panne_courante(self):
		for p in self.env['maintenance.panne'].search([]):
			p.panne_courante = False
		for p in self.env['maintenance.panne'].search([], limit=5, order='occurrence_panne desc'):
			p.panne_courante = True

	name = fields.Char('Panne', required=True)
	description = fields.Text('Description')
	occurrence_panne = fields.Integer(compute='_get_occurrence_panne', string="Nombre d\'occurrence", store=True)
	demande_intervention_ids = fields.One2many('maintenance.demande.intervention', 'panne_id', 'Demande intervention')
	panne_courante = fields.Boolean(compute='_get_panne_courante', string='Panne courante', store=True)

#----------------------------------------------------------
# maintenance_demande_intervention
#----------------------------------------------------------
class maintenance_demande_intervention(models.Model):
	_name = 'maintenance.demande.intervention'
	_rec_name = 'reference_intervention'

	#button workflow annuler
	@api.one
	def action_annuler(self):
		self.write({'state': 'annule'})

	#button workflow planifier
#	@api.one
#	def action_planifier(self):
#		self.write({'state': 'planifie'})

	#button workflow traiter
#	@api.one
#	def action_traiter(self):
#		self.write({'state': 'traite'})

#		#creer demande intervention
#		if self.maintenance_preventive_id and self.maintenance_preventive_id.type_intervalle == 'intervalle': 
#			intervalle = self.maintenance_preventive_id.intervalle
#			date_planifie = datetime.datetime.now() + datetime.timedelta(days=intervalle)
#			self.env['maintenance.demande.intervention'].create({'machine_id': self.machine_id.id,
#																'maintenance_preventive_id': self.maintenance_preventive_id.id,
#																'panne_id': self.panne_id.id,
#																'date_entretien_planifie': date_planifie})

#		if self.maintenance_preventive_id and self.maintenance_preventive_id.type_intervalle == 'duree': 
#			date_planifie = datetime.datetime.now() + datetime.timedelta(days=self.maintenance_preventive_id.duree)
#			duree_planifie = self.maintenance_preventive_id.duree * 7 + self.machine_id.duree_fonctionnement
#			self.env['maintenance.demande.intervention'].create({'machine_id': self.machine_id.id,
#																'maintenance_preventive_id': self.maintenance_preventive_id.id,
#																'panne_id': self.panne_id.id,
#																'date_entretien_planifie': date_planifie,
#																'duree_planifie': duree_planifie})

	#button workflow evaluer
#	@api.one
#	def action_evaluer(self):
#		self.write({'state': 'evalue'})

	#button workflow cloturer
	@api.one
	def action_cloturer(self):
		self.write({'state': 'cloture'})

	@api.one
#	@api.depends('date_entretien_planifie')
	def _get_jours_restants(self):
		if self.date_entretien_planifie:
			dt_p = datetime.datetime.fromtimestamp(time.mktime(time.strptime(self.date_entretien_planifie, "%Y-%m-%d %H:%M:%S")))
			jours_restants = dt_p - datetime.datetime.now()
			self.jours_restants = jours_restants.days

	@api.one
#	@api.depends('duree_planifie')
	def _get_duree_restants(self):
		if self.duree_planifie:
			self.duree_restants = self.duree_planifie - self.machine_id.duree_fonctionnement

	@api.one
	@api.depends('heure_travaillee', 'cout_horaire')
	def _calcul_cout(self):
		for rec in self:
			if rec.cout_horaire and rec.heure_travaillee:
				self.cout = rec.cout_horaire * rec.heure_travaillee

	@api.one
	def _get_delai(self):
		if self.date_entretien_planifie:
			dt_p = datetime.datetime.fromtimestamp(time.mktime(time.strptime(self.date_entretien_planifie, "%Y-%m-%d %H:%M:%S")))
			jours_restants = dt_p - datetime.datetime.now()
			if jours_restants.days > 0 and jours_restants.days <= 10:
				self.delai = 'orange'
			elif jours_restants.days > 10:
				self.delai = 'vert'
			else:
				self.delai = 'rouge'

	reference_intervention = fields.Char('Référence', default='/', required=True)
	#demande
	demandeur = fields.Char('Demandeur')
	maintenance_preventive_id = fields.Many2one('maintenance.preventive', 'Référence MP', ondelete='cascade')
	type_intervalle_rel = fields.Selection([('duree','Durée de fonctionnement'),
											('intervalle','Intervalle')], string='Type',
											related='maintenance_preventive_id.type_intervalle')	
	date_demande = fields.Datetime('Date demande', default= lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'))
	machine_id = fields.Many2one('production.machine', 'Machine', required=True, ondelete='cascade')
	panne_id = fields.Many2one('maintenance.panne', 'Panne?', required=True, ondelete='cascade')
	priorite = fields.Selection([('basse','Basse'),
								 ('normal','Normal'),
								 ('urgent','Urgent'),
								 ('autres','Autres')], 'Priorité', default='normal')
	jours_restants = fields.Integer(compute='_get_jours_restants', string='Delai (j)')
	duree_restants = fields.Integer(compute='_get_duree_restants', string='Durée restants (h)')

	#planification
	type_prestataire = fields.Selection([('externe','Externe'),
										 ('interne','Interne')], 'Type prestataire', default='externe')
	prestataire_id = fields.Many2one('maintenance.prestataire', 'Prestataire', ondelete='cascade')
	operateur_id = fields.Many2one('production.operateur', 'Operateur', ondelete='cascade')
	date_entretien_planifie = fields.Datetime('Date entretien planifiée')
	duree_planifie = fields.Float('Durée de fonctionnement planifiée')
	#traitement
	traitement_effectue = fields.Text('Traitement effectué')
	demande_intervention_piece_rel_ids = fields.One2many('demande.intervention.piece.rel', 'demande_intervention_id', 'Pièces de rechange')
	date_entretien = fields.Datetime('Date début entretien')
	date_fin_entretien = fields.Datetime('Date fin entretien')

	heure_travaillee = fields.Integer('Heure travaillée')
	cout_horaire = fields.Float('Coût horaire', related="operateur_id.cout_horaire")
	cout = fields.Float(compute='_calcul_cout', string='Coût')
	montant_facture = fields.Float('Montant facturé')
	temp_arret = fields.Float('temp d\'arrêt (h)')

	#evaluation
	date_evaluation = fields.Date('Date évaluation')

	remarque = fields.Text('Remarque')
	state = fields.Selection([('non_planifie', 'Non planifié'),
							  ('planifie', 'Planifiée'),
							  ('traite', 'Traitée'),
							  ('evalue', 'Evaluée'),
							  ('cloture', 'Cloturée'),
							  ('annule', 'Annulée')], 'Etat', required=True, default='non_planifie')

	delai = fields.Selection([('vert','vert'),
							('rouge','rouge'),
							('orange','orange')], compute='_get_delai', string='Delai')

	@api.model
	def create(self, values):
		#generer code sequence "reference_intervention" s'il n'est pas spécifié
		if ('reference_intervention' not in values) or (values.get('reference_intervention')=='/'):
			values['reference_intervention'] = self.env['ir.sequence'].get('maintenance.demande.intervention')

		#test reference_intervention doit etre unique
		if self.env['maintenance.demande.intervention'].search_count([('reference_intervention', '=', values['reference_intervention'])]) > 0:
			raise Warning(_('Erreur!'), 
						_('Référence intervention existe déjà [ %s ].')% (values['reference_intervention']))

		return super(maintenance_demande_intervention, self).create(values)

	@api.multi
	def write(self, values):
		obj_id=super(maintenance_demande_intervention, self).write(values)
		#test reference_intervention doit etre unique
		if self.env['maintenance.demande.intervention'].search_count([('reference_intervention', '=', self.reference_intervention)]) > 1:
			raise Warning(_('Erreur!'), 
						_('Référence intervention existe déjà [ %s ].')% (self.reference_intervention))

		return obj_id

	@api.multi
	def evaluer_prestataire(self):
		self.date_evaluation = datetime.date.today()
		self.state = 'evalue'
		return { 
				'name': _("Evaluation"),
				'type': 'ir.actions.act_window',
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'maintenance.evaluation.prestataire',
				'view_id': False,
				'target': 'new',
				'context': {'default_maintenance_prestataire_id': self.prestataire_id.id,
							'default_demande_intervention_id': self.id,
							'default_delai_prevu': self.date_entretien_planifie,
							'default_delai_reel': self.date_entretien,
							'default_maintenance_corrective_id': self.id,
							},
				}

	@api.multi
	def evaluer_operateur(self):
		self.date_evaluation = datetime.date.today()
		self.state = 'evalue'
		return { 
				'name': _("Evaluation"),
				'type': 'ir.actions.act_window',
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'maintenance.evaluation.operateur',
				'view_id': False,
				'target': 'new',
				'context': {'default_production_operateur_id': self.operateur_id.id,
							'default_date_evaluation': self.date_evaluation,
							},
				}

#----------------------------------------------------------
# maintenance_evaluation_operateur
#----------------------------------------------------------
class maintenance_evaluation_operateur(models.Model):
	_name = 'maintenance.evaluation.operateur'

	production_operateur_id = fields.Many2one('production.operateur', 'Operateur', ondelete='cascade')
	qualite_service = fields.Selection([('0', '0/20'),
										('1', '5/20'),
										('2', '10/20'),
										('3', '15/20'),
										('4', '20/20'),], string="Efficacité (/20)", default='0')
	date_evaluation = fields.Date('Date évaluation')

#----------------------------------------------------------
# maintenance_prestataire
#----------------------------------------------------------
class maintenance_prestataire(models.Model):

	@api.multi
	@api.depends('name', 'note_moyenne')
	def name_get(self):
		result = []
		for record in self:
			note_moyenne = str(record.note_moyenne) if record.note_moyenne != False else ''
			result.append((record.id, record.name + ' ( ' + note_moyenne + ' /20)')) 
		return result

	_name = 'maintenance.prestataire'

	@api.one
	def _get_note_moyenne(self):
		total = 0.0
		con = 0.0
		for m in self:
			for e in m.evaluation_ids:
				total += e.note
				con += 1

		if con > 0:
			self.note_moyenne = total / con

	name = fields.Char('Nom', required=True)
	evaluation_ids = fields.One2many('maintenance.evaluation.prestataire', 'maintenance_prestataire_id', 'Evaluations')
	note_moyenne = fields.Float(compute='_get_note_moyenne', string="Note moyenne")

#----------------------------------------------------------
# maintenance_evaluation_prestataire
#----------------------------------------------------------
class maintenance_evaluation_prestataire(models.Model):
	_name = 'maintenance.evaluation.prestataire'

	@api.one
	@api.depends('delai_prevu', 'delai_reel')
	def _get_ecart(self):
		if self.delai_prevu and self.delai_reel:
			d_prevu = datetime.datetime.strptime(self.delai_prevu, '%Y-%m-%d')
			d_reel = datetime.datetime.strptime(self.delai_reel, '%Y-%m-%d')

			self.ecart = (d_reel-d_prevu).days

	@api.one
	@api.depends('qualite_service', 'ecart')
	def _get_note(self):
		n = 0
		if self.qualite_service == '2':
			n += 15
		elif self.qualite_service == '1':
			n += 5
		if self.ecart <= 0:
			n += 5
		self.note = n

	@api.one
	@api.depends('note')
	def _get_decision(self):
		if self.note == 20:
			self.decision = 'agree'
		elif self.note == 15:
			self.decision = 'surveiller_delais'
		elif self.note == 10:
			self.decision = 'surveiller_qualite'
		else:
			self.decision = 'eliminer'

	maintenance_prestataire_id = fields.Many2one('maintenance.prestataire', 'Prestataire', ondelete='cascade')
	demande_intervention_id = fields.Many2one('maintenance.demande.intervention', 'Référence', ondelete='cascade')
	qualite_service = fields.Selection([('0', 'Sans impact/Impact négatif(0)'),
										('1', 'Impact médiocre(5)'),
										('2', 'Impact positif(15)'),], string="Qualité de service", default='0')
	delai_prevu = fields.Date('Délai prévu')
	delai_reel = fields.Date('Délai réel')
	ecart = fields.Integer(compute='_get_ecart', string='Ecart(jours)')
	note = fields.Float(compute='_get_note', string='Note/20')
	decision = fields.Selection(compute='_get_decision', 
								selection=[ ('agree', 'Prestataire agrée'),
											('surveiller_qualite', 'Prestataire à surveiller en qualité'),
											('surveiller_delais', 'Prestataire à surveiller en délais'),
											('eliminer', 'Prestataire à éliminer')], 
								string='Décision')

#----------------------------------------------------------
# demande_intervention_piece_rel
#----------------------------------------------------------
class demande_intervention_piece_rel(models.Model):
	_name = 'demande.intervention.piece.rel'

	demande_intervention_id = fields.Many2one('maintenance.demande.intervention', 'Demande intervention', ondelete='cascade')
	piece_id = fields.Many2one('maintenance.piece', 'Pièce', required=True, ondelete='cascade')
	quantite = fields.Float('Quantité', required=True)
	unite = fields.Selection([('kg','kg'),
							  ('U','U'),
							  ('m','m'),
							  ('m2','m²'),
							  ('m3','m³'),
							  ('l','l'),], related='piece_id.unite', readonly=True)
	prix = fields.Float('Prix unitaire (DT)', related='piece_id.prix', readonly=True)
	date = fields.Date('Date', default= lambda *a:datetime.datetime.now().strftime('%Y-%m-%d'), required=True)

	@api.model
	def create(self, values):
		#test quantite <= 0
		if values['quantite'] <= 0:
			raise Warning(_('Erreur!'), 
						_('La quantité piéce doit être positive'))

		#retirer du stock la quantite des pieces utilisé
		for piece in self.env['maintenance.piece'].browse(values['piece_id']):
			piece.quantite_stock -= values['quantite']

		return super(demande_intervention_piece_rel, self).create(values)

	@api.multi
	def write(self, values):
		nouv_quantite = values.get('quantite', None)
		nouv_piece_id = values.get('piece_id', None)
		ancien_piece_obj = self.env['maintenance.piece'].browse(self.piece_id.id)


		#test si quantite <= 0 on genere exception
		if nouv_quantite:
			if nouv_quantite <= 0:
				raise Warning(_('Erreur!'), 
							_('La quantité doit étre supérieur strictement à zero ( %s )')% (nouv_quantite))

		#modifier stock
		if nouv_piece_id:
			nouv_piece_obj = self.env['maintenance.piece'].browse(nouv_piece_id)
			if nouv_quantite:
				ancien_piece_obj.quantite_stock += self.quantite
				nouv_piece_obj.quantite_stock -= nouv_quantite
			else:#quantite non changer
				ancien_piece_obj.quantite_stock += self.quantite
				nouv_piece_obj.quantite_stock -= self.quantite
		else:#piece non changer
			if nouv_quantite:
				ancien_piece_obj.quantite_stock += self.quantite
				ancien_piece_obj.quantite_stock -= nouv_quantite

		obj_id=super(demande_intervention_piece_rel, self).write(values)

		return obj_id

	@api.multi
	def unlink(self):
		for rec in self:
			#ajouter la quantite du stock retirer
			piece_obj = self.env['maintenance.piece'].browse(rec.piece_id.id)
			piece_obj.quantite_stock += rec.quantite

		return super(demande_intervention_piece_rel, self).unlink()
#----------------------------------------------------------
# maintenance_preventive
#----------------------------------------------------------
class maintenance_preventive(models.Model):
	_name = 'maintenance.preventive'
	_rec_name = 'reference_maintenance_preventive'

	reference_maintenance_preventive = fields.Char('Référence', default='/', required=True)
	machine_id = fields.Many2one('production.machine', 'Machine', required=True, ondelete='cascade')
	type_intervalle = fields.Selection([('duree','Durée de fonctionnement'),
										('intervalle','Intervalle')], string='Type', default='intervalle', required=True)
	intervalle = fields.Integer('Intervalle (en jours)')
	duree = fields.Integer('Durée (en jours)')
	commence_le = fields.Date('Commencé le', default= lambda *a:datetime.datetime.now().strftime('%Y-%m-%d'), required=True)
	panne_id = fields.Many2one('maintenance.panne', 'Intervention', required=True, ondelete='cascade')
	demande_intervention_ids = fields.One2many('maintenance.demande.intervention', 'maintenance_preventive_id', 
												'Demandes d\'intervention')

	@api.model
	def create(self, values):
		#test intervalle et duree doivent etre > 0
		if values['type_intervalle'] == 'intervalle' and values['intervalle'] <= 0:
			raise Warning(_('Erreur!'), 
						_('Il faut que :  intervalle > 0'))
		if values['type_intervalle'] == 'duree' and values['duree'] <= 0:
			raise Warning(_('Erreur!'), 
						_('Il faut que :  duree > 0'))

		#generer code sequence "reference_maintenance_preventive" s'il n'est pas spécifié
		if ('reference_maintenance_preventive' not in values) or (values.get('reference_maintenance_preventive')=='/'):
			values['reference_maintenance_preventive'] = self.env['ir.sequence'].get('maintenance.preventive')

		#test reference_maintenance_preventive doit etre unique
		if self.env['maintenance.preventive'].search_count([('reference_maintenance_preventive', '=', values['reference_maintenance_preventive'])]) > 0:
			raise Warning(_('Erreur!'), 
						_('Référence maintenance préventive existe déjà [ %s ].')% (values['reference_maintenance_preventive']))

		new_id = super(maintenance_preventive, self).create(values)

		#creer demande intervention
		if values['type_intervalle'] == 'intervalle':
			#date_planifie = datetime.datetime.now() + datetime.timedelta(days=values['intervalle'])
			date_planifie = datetime.datetime.strptime(values['commence_le'], '%Y-%m-%d') + datetime.timedelta(days=values['intervalle'])
			self.env['maintenance.demande.intervention'].create({'machine_id': values['machine_id'],
																'maintenance_preventive_id': new_id.id,
																'panne_id': values['panne_id'],
																'date_entretien_planifie': date_planifie,
																'state': 'planifie'})
		if values['type_intervalle'] == 'duree':
			m_obj = self.env['production.machine'].browse(values['machine_id'])
			#date_planifie = datetime.datetime.now() + datetime.timedelta(days=values['duree'])
			date_planifie = datetime.datetime.strptime(values['commence_le'], '%Y-%m-%d') + datetime.timedelta(days=values['duree'])
			duree_planifie = m_obj.duree_fonctionnement + values['duree'] * 7
			self.env['maintenance.demande.intervention'].create({'machine_id': values['machine_id'],
																'maintenance_preventive_id': new_id.id,
																'panne_id': values['panne_id'],
																'date_entretien_planifie': date_planifie,
																'state': 'planifie',
																'duree_planifie': duree_planifie})

		return new_id

	@api.multi
	def write(self, values):
		obj_id=super(maintenance_preventive, self).write(values)
		for obj in self:
			#test intervalle et duree doivent etre > 0
			if obj.type_intervalle == 'intervalle' and obj.intervalle <= 0:
				raise Warning(_('Erreur!'), 
						_('Il faut que :  intervalle > 0'))
			if obj.type_intervalle == 'duree' and obj.duree <= 0:
				raise Warning(_('Erreur!'), 
						_('Il faut que :  duree > 0'))


		#test reference_maintenance_preventive doit etre unique
		if self.env['maintenance.preventive'].search_count([('reference_maintenance_preventive', '=', self.reference_maintenance_preventive)]) > 1:
			raise Warning(_('Erreur!'), 
						_('Référence maintenance préventive existe déjà [ %s ].')% (self.reference_maintenance_preventive))

		return obj_id


