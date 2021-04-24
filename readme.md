## Module production odoo
le module production contient quatre sous modules . chaque sous-module est représenté par un fichier controlleur(.py) qui contient les attributs et les fonctions et un fichier vue(.xml) pour representation des données.

## Sous modules production
* la gestion de production    (production.py,production_view.xml)
* la gestion de maintenance   (maintenance.py,maintenance_view.xml)
* la gestion d'achat    (achat.py,achat_view.xml)
* la gestion de vente    (vente.py,vente_view.xml)

## Architecture
le module production contient 6 dossiers chacun à une fonction bien déterminée:

* le dossier data : il inclut tous les fichiers (.csv) pour l'importation des données exemple les articles, les machines, les opérateurs, les fournisseurs et le client odoo font l'importation automatique lorsque le module s'installe
* le dossier report : contient les fichiers de rapport (*. Jrxml,* .jasper) Nécessaire pour la preparation à l'impression a travers odoo(il est utilisé pour l'impression d'Of)
* le dossier satic : contient les ressources(*.Css,*. js, les images) utilisé par odoo
* le dossier wizard:
* le dossier security : contient les les listes des groupes la langue du système et le s droits d'accès
* le dossier views :utile pour changer la template par défaut 

nb: il y a 2 fichiers __init__. py et Openerp.py qui sont indispensables pour le chargement et la déclaration de module



