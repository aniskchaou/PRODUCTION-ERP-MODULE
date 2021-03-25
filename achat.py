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
# article_commande_fournisseur_rel
#----------------------------------------------------------
class article_commande_fournisseur_rel(models.Model):

	_name = "article.commande.fournisseur.rel"
	
	commande_fournisseur_id = fields.Many2one('commande.fournisseur', 'Commande', ondelete='cascade', required=True)
	article_id = fields.Many2one('production.article', 'Article', ondelete='cascade', required=True)
	quantite = fields.Float('Quantité commandé', required=True)
	unite = fields.Selection([('u','U'),
							  ('kg','Kg'),
							  ('m2','m²'),
							  ('m','m')], related='article_id.unite', readonly=True, string='Unite')

	quantite_livre = fields.Float(compute='_get_quantite_livre', string='Quantité livré', readonly=True)
	progress = fields.Float(compute='_get_progress', string='Progression')

	stock_reel = fields.Float(string='Stk_Réel', related='article_id.stock_reel')
	stock_disponible = fields.Float('Stk_Dispo', related='article_id.stock_disponible')
	stock_non_reserve = fields.Float(string='Stk_Non_Rés', related='article_id.stock_non_reserve')

	state = fields.Selection([('brouillon','Brouillon'),
				   			  ('annulee','Annulée'),
				   			  ('attente','En attente de réception'),
				   			  ('recu_partiel','Reçu partiellemet'),
				  			  ('recu_total','Reçu totalemet'),], 'Etat', related='commande_fournisseur_id.state')

	@api.one
	@api.depends('commande_fournisseur_id', 'article_id')
	def _get_quantite_livre(self):
		for line in self:
			qte = 0
			bea_ids = self.env['bon.entree.achat'].search([('commande_id', '=', line.commande_fournisseur_id.id), 
														   ('article_id', '=', line.article_id.id)])
			for bea in bea_ids:
				qte += bea.quantite
			self.quantite_livre = qte

	@api.one
	@api.depends('quantite', 'quantite_livre')
	def _get_progress(self):
		if self.quantite > 0 and self.quantite_livre > 0:
			self.progress = self.quantite_livre / self.quantite * 100
		else:
			self.progress = 0


	@api.model
	def create(self, values):
		#test si quantite <= 0 on genere exception
		if values['quantite'] <= 0:
			raise Warning(_('Erreur!'), 
						_("La quantité commandé doit étre supérieur strictement à zero"))

		new_id = super(article_commande_fournisseur_rel, self).create(values)
		return new_id

	@api.multi
	def write(self, values):
		obj_id=super(article_commande_fournisseur_rel, self).write(values)
		for obj in self:
			#test si quantite <= 0 on genere exception
			if obj.quantite <= 0:
				raise Warning(_('Erreur!'), 
							_("La quantité commandé doit étre supérieur strictement à zero"))

		return obj_id

	@api.multi
	def ajouter_bon_entree_achat(self):
		return {
			'name': _("Bon entrée achat"),
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'bon.entree.achat',
			'view_id': False,
			'context': {
					'default_commande_id': self.commande_fournisseur_id.id,
					'default_article_id': self.article_id.id},
					}

#----------------------------------------------------------
# commande_fournisseur
#----------------------------------------------------------
class commande_fournisseur(models.Model):

	@api.one
	@api.depends('state')
	def _check_color(self):
		for rec in self:
			color = 0
			color_value = self.env['color.status'].search([('state', '=', rec.state)], limit=1).color
			if color_value:
				color = color_value

			self.member_color = color

	#button workflow Envoyer
	@api.one
	def action_envoyer_commande(self):
		if self.article_commande_fournisseur_ids:
			self.write({'state': 'attente'})
		else:
			raise Warning(_('Erreur!'), 
						_("Cette commande (%s) ne contient aucun article") % self.code_commande)

	#button workflow Cloturer
	@api.one
	def action_cloturer_commande(self):
		total = True
		for line in self.article_commande_fournisseur_ids:
			if line.quantite_livre < line.quantite:
				total = False
				break
		if total == True:
			self.write({'state': 'recu_total'})
		else:
			self.write({'state': 'recu_partiel'})

	#button workflow Annuler
	@api.one
	def action_annuler_commande(self):
		self.write({'state': 'annulee'})

	_name = 'commande.fournisseur'
	_rec_name = 'code_commande'

	member_color = fields.Integer(compute='_check_color', string='Color')
	code_commande = fields.Char('Code commande :', required=True)
	fournisseur_id = fields.Many2one('achat.fournisseur', 'Fournisseur', required=True, ondelete='cascade')
	date_commande = fields.Date('Date de commande', required=True, default= lambda *a:datetime.now().strftime('%Y-%m-%d'))
	article_commande_fournisseur_ids = fields.One2many('article.commande.fournisseur.rel', 'commande_fournisseur_id', 'Articles')
	bon_entree_achat_ids = fields.One2many('bon.entree.achat', 'commande_id', 'Bons entrées achat')
	state = fields.Selection([('brouillon','Brouillon'),
							  ('annulee','Annulée'),
							  ('attente','En attente de réception'),
							  ('recu_partiel','Reçu partiellemet'),
							  ('recu_total','Reçu totalemet'),], 'Etat', readonly=True, default='brouillon')

	@api.model
	def create(self, values):
		#test code_commande doit etre unique
		if self.env['commande.fournisseur'].search_count([('code_commande', '=', values['code_commande'])]) > 0:
			raise Warning(_('Erreur!'),
						_('Code commande existe déjà [ %s ].')% (values['code_commande']))

		#test si le même article ajouté plusieur fois on génére exception
		ids = []
		articles = values.get("article_commande_fournisseur_ids", None)
		for article in articles:
			article_id = article[2].get("article_id", None)
			if article_id and article_id in ids:
				artcile_obj = self.env['production.article'].browse(article_id)
				raise Warning(_('Erreur!'), 
							_("Même article ajouté plusieurs fois : %s") % artcile_obj.code_article)
			ids.append(article_id)

		new_id = super(commande_fournisseur, self).create(values)
		return new_id

	@api.multi
	def write(self, values):
		obj_id = super(commande_fournisseur, self).write(values)
		#test code_commande doit etre unique
		if self.env['commande.fournisseur'].search_count([('code_commande', '=', self.code_commande)]) > 1:
			raise Warning(_('Erreur!'),
						_('Code commande existe déjà [ %s ].')% (self.code_commande))

		#test si le même article ajouté plusieur fois on génére exception
		ids = []
		for line in self.article_commande_fournisseur_ids:
			if line.article_id.id in ids:
				raise Warning(_('Erreur!'), 
							_("Même article ajouté plusieurs fois : %s") % line.article_id.code_article)
			ids.append(line.article_id.id)
	    
		return obj_id

#----------------------------------------------------------
# bon_entree_achat
#----------------------------------------------------------
class bon_entree_achat(models.Model):

	@api.one
	@api.depends('article_id', 'commande_id')
	def _get_quantite_commande(self):
		if self.article_id and self.commande_id:
			self.quantite_commande = self.env['article.commande.fournisseur.rel'].search([
																	('article_id', '=', self.article_id.id), 
																  	('commande_fournisseur_id', '=', self.commande_id.id)], 
																	limit=1).quantite

	@api.one
	@api.depends('article_id', 'commande_id')
	def _get_quantite_livre(self):
		qte = 0
		if self.commande_id and self.article_id:
			bon_entree_achat_ids = self.env['bon.entree.achat'].search([('commande_id', '=', self.commande_id.id), 
																		('article_id', '=', self.article_id.id)])
			for bea in bon_entree_achat_ids:
				qte += bea.quantite

		self.quantite_livre = qte

	@api.one
	@api.depends('quantite_commande', 'quantite_livre')
	def _get_progress(self):
		if self.quantite_commande > 0 and self.quantite_livre > 0:
			self.progress = self.quantite_livre / self.quantite_commande * 100
		else:
			self.progress = 0

	_name = 'bon.entree.achat'
	_rec_name = 'code_bon'

	code_bon = fields.Char('Code bon :', readonly=True)
	date_bon = fields.Date('Date', required=True, default= lambda *a:datetime.now().strftime('%Y-%m-%d'))
	commande_id = fields.Many2one('commande.fournisseur', 'Commande', required=True, ondelete='cascade', 
									domain="[('state', '=', 'attente')]" )
	article_id = fields.Many2one('production.article', 'Article', required=True, ondelete='cascade')
	quantite = fields.Float('Quantité',required=True)
	unite = fields.Selection([('u','U'),
				   			  ('kg','Kg'),
				   			  ('m2','m²'),
				   			  ('m','m')], related='article_id.unite', readonly=True, string='Unite')
	quantite_commande = fields.Float(compute='_get_quantite_commande', string='Quantité commandé')
	quantite_livre = fields.Float(compute='_get_quantite_livre', string='Quantité livré')
	progress = fields.Float(compute='_get_progress', string='Progression')

	@api.model
	def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
		res = super(bon_entree_achat, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
		for field in res['fields']:
			if field == 'article_id':
				res['fields'][field]['domain'] = [('id','in', [])]

		return res

	@api.model
	def create(self, values):
		#test si quantite <= 0 on genere exception
		if values['quantite'] <= 0:
			raise Warning(_('Erreur!'), 
						_("La quantité doit étre supérieur strictement à zero"))

		#generer code sequence "code_bon"
		values['code_bon'] = self.env['ir.sequence'].get('bon.entree.achat')

		#augmenter stock
		for article in self.env['production.article'].browse(values['article_id']):
			article.stock_reel += values['quantite']

			#test stock maximale
			article.verifier_stock()

		new_id = super(bon_entree_achat, self).create(values)
		return new_id

	@api.multi
	def write(self, values):

		nouv_article = values.get('article_id', None)
		nouv_quantite = values.get('quantite', None)
		ancien_article_obj = self.env['production.article'].browse(self.article_id.id)

		if nouv_article:
			nouv_article_obj = self.env['production.article'].browse(nouv_article)
			if nouv_quantite:
				#test si quantite <= 0 on genere exception
				if nouv_quantite <= 0:
					raise Warning(_('Erreur!'), 
								_('La quantité doit étre supérieur strictement à zero'))

				#modifier stock
				ancien_article_obj.stock_reel -= self.quantite
				nouv_article_obj.stock_reel += nouv_quantite

			else:#si quantite non changer
				#modifier stock
				ancien_article_obj.stock_reel -= self.quantite
				nouv_article_obj.stock_reel += self.quantite
		else:#si article non changer
			if nouv_quantite:
				#test si quantite <= 0 on genere exception
				if nouv_quantite <= 0:
					raise Warning(_('Erreur!'), 
								_('La quantité doit étre supérieur strictement à zero'))

				#modifier stock
				ancien_article_obj.stock_reel += nouv_quantite - self.quantite


		obj_id=super(bon_entree_achat, self).write(values)

		return obj_id

	@api.multi
	def unlink(self):
		for rec in self:
			article_obj = self.env['production.article'].browse(rec.article_id.id)
			article_obj.stock_reel -= rec.quantite

		return super(bon_entree_achat, self).unlink()

	@api.onchange('commande_id')
	def onchange_commande_id(self):
		res = {}
		ids = []
		default_commande = self._context.get('default_commande_id', False)
		default_article = self._context.get('default_article_id', False)
		if self.commande_id:
			if default_article == False:
			    self.article_id = []
			if default_commande:
				if self.commande_id.id != default_commande:
					self.article_id = []
			#filter sur le champ article_id selon commande_id séléctionné
			for ligne in self.commande_id.article_commande_fournisseur_ids:
				ids.append(ligne.article_id.id)

		else:#si commande_id vide
			self.article_id = []

		res['domain'] = {'article_id': [('id', 'in', ids)]}
		return res


#----------------------------------------------------------
# demande_achat
#----------------------------------------------------------
class demande_achat(models.Model):

	_name = 'demande.achat'

	date_demande = fields.Date('Date demande', default= lambda *a:datetime.now().strftime('%Y-%m-%d'))
	demandeur = fields.Many2one('res.users', 'Demandeur', default= lambda self: self.env.user)
	article_id = fields.Many2one('production.article', 'Article', ondelete='cascade', required=True)
	quantite_demande = fields.Float('Quantité demandé', required=True)



