le module production contient quatre sous modules . chaque sous-module est représenté par un fichier controlleur(.py) qui contient les attributs et les fonctions et un fichier vue(.xml) pour representation des données.

1)la gestion de production    (production.py,production_view.xml)
2)la gestion de maintenance   (maintenance.py,maintenance_view.xml)
3)la gestion d'achat    (achat.py,achat_view.xml)
4)la gestion de vente    (vente.py,vente_view.xml)







-le module production contient 6 dossiers chacun à une fonction bien déterminée:
1)le dossier data : il inclut tous les fichiers (.csv) pour l'importation des données exemple les articles, les machines, les opérateurs, les fournisseurs et le client odoo font l'importation automatique lorsque le module s'installe
2)le dossier report : contient les fichiers de rapport (*. Jrxml,* .jasper) Nécessaire pour la preparation à l'impression a travers odoo(il est utilisé pour l'impression d'Of)
3)le dossier satic : contient les ressources(*.Css,*. js, les images) utilisé par odoo
4)le dossier wizard:
5)le dossier security : contient les les listes des groupes la langue du système et le s droits d'accès
6)le dossier views :utile pour changer la template par défaut 

nb: il y a 2 fichiers __init__. py et Openerp.py qui sont indispensables pour le chargement et la déclaration de module



les modifications effectué dans le module production


-faire l'insertion de bon de reservation automatiquement (dans le fichier production.py)

1)(ligne 2517):
        

        if values['quantite'] > article_obj.stock_non_reserve:
           #self.write({'etat': 'nonsatisfait'})
           #print 'non satisfait'
           values['etat']='nonsatisfait'
2)(ligne 1743)
   
    self.env['bon.reservation.ordre.fabrication'].create({'code_bon':'OF','date_bon':datetime.now().strftime('%Y-%m-%d'),'ordre_fabrication_id':id_of.id,'article_id':values['article_entree1'],'quantite':values['quantite1'],'quantite_demande':values['quantite1']})
        if values['article_entree2']:
           self.env['bon.reservation.ordre.fabrication'].create({'code_bon':'OF','date_bon':datetime.now().strftime('%Y-%m-%d'),'ordre_fabrication_id':id_of.id,'article_id':values['article_entree2'],'quantite':values['quantite2'],'quantite_demande':values['quantite2']})


-ajouter afficher menu 'Bon de reservation OF' odoo-8/openerp/addons/gestionproduction2/gestionproduction_view.xml 

(ligne 53)

 <menuitem name="Bon de Reservation OF" id="bon_reservation_menu_item" parent="production_main_menu" action="production.action_bon_reservation_ordre_fabrication"/>

