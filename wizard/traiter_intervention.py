# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import datetime

class traiter_intervention(models.TransientModel):
	"""Traiter intervention"""
	_name = "traiter.intervention"

	demande_intervention_id = fields.Many2one('maintenance.demande.intervention', 'Demande intervention', ondelete='cascade')
	traitement_effectue = fields.Text('Traitement effectué')
	demande_intervention_piece_rel_ids = fields.One2many('traiter.intervention.piece.rel', 'demande_intervention_id', 'Pièces de rechange')
	date_entretien = fields.Datetime('Date début entretien')
	date_fin_entretien = fields.Datetime('Date fin entretien')
	heure_travaillee = fields.Integer('Heure travaillée')
	montant_facture = fields.Float('Montant facturé')
	temp_arret = fields.Float('temp d\'arrêt (h)')

	@api.one
	def traiter_intervention(self):
		line_ids = []
		for data in self:
			if self._context.get('active_id', False):
				for line in data.demande_intervention_piece_rel_ids:
					line_ids.append((0,0,{'demande_intervention_id': data.demande_intervention_id, 
										'piece_id': line.piece_id.id,
										'quantite': line.quantite,
										'date': line.date}))
					#retirer qte stock
					qte_stock = self.env['maintenance.piece'].browse(line.piece_id.id).quantite_stock
					qte_stock -= line.quantite

				#creer demande intervention
				if data.demande_intervention_id.maintenance_preventive_id and data.demande_intervention_id.maintenance_preventive_id.type_intervalle == 'intervalle': 
					intervalle = data.demande_intervention_id.maintenance_preventive_id.intervalle
					date_planifie = datetime.datetime.now() + datetime.timedelta(days=intervalle)
					self.env['maintenance.demande.intervention'].create({
										'machine_id': data.demande_intervention_id.machine_id.id,
										'maintenance_preventive_id': data.demande_intervention_id.maintenance_preventive_id.id,
										'panne_id': data.demande_intervention_id.panne_id.id,
										'date_entretien_planifie': date_planifie,
										'state': 'planifie',})

				if data.demande_intervention_id.maintenance_preventive_id and data.demande_intervention_id.maintenance_preventive_id.type_intervalle == 'duree': 
					date_planifie = datetime.datetime.now() + datetime.timedelta(days=data.demande_intervention_id.maintenance_preventive_id.duree)
					duree_planifie = data.demande_intervention_id.maintenance_preventive_id.duree * 7 + data.demande_intervention_id.machine_id.duree_fonctionnement
					self.env['maintenance.demande.intervention'].create({
										'machine_id': data.demande_intervention_id.machine_id.id,
										'maintenance_preventive_id': data.demande_intervention_id.maintenance_preventive_id.id,
										'panne_id': data.demande_intervention_id.panne_id.id,
										'date_entretien_planifie': date_planifie,
										'state': 'planifie',
										'duree_planifie': duree_planifie})

				self.env['maintenance.demande.intervention'].browse(self._context.get('active_id', False)).write({'traitement_effectue': data.traitement_effectue, 'demande_intervention_piece_rel_ids': line_ids, 'date_entretien': data.date_entretien, 'date_fin_entretien': data.date_fin_entretien, 'heure_travaillee': data.heure_travaillee, 'montant_facture': data.montant_facture, 'temp_arret': data.temp_arret, 'state': 'traite'})

class traiter_intervention_piece_rel(models.TransientModel):
	_name = 'traiter.intervention.piece.rel'

	demande_intervention_id = fields.Many2one('traiter.intervention', 'Demande intervention', ondelete='cascade')
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


