// Noya Home — wave 2 (organic reach): education carousels + choice/duel images.
// Only general, verifiable advice; brand facts limited to: 69 wilayas delivery, cash on delivery.
export type Pt = {h: string; t?: string; img?: string};
export type Edu = {id: string; label: string; title: string; cover: string; points: Pt[]; end: string};
export type Choice = {id: string; title: string; items: {l: string; name: string; img: string}[]; foot: string};

export const EDU: Edu[] = [
  {id: 'E_ERREURS', label: 'DÉCO', title: '3 erreurs qui font paraître\nun salon moins cher', cover: 'real/A_1', points: [
    {h: 'Une table basse mal proportionnée', t: 'Trop grande, elle bloque le passage. Trop petite, elle disparaît. Visez environ 2/3 de la longueur du canapé.', img: 'ORION'},
    {h: 'Trop de matières et de couleurs', t: 'Gardez 2 ou 3 matières qui se répondent : bois, tissu, pierre ou verre.', img: 'real/E_0'},
    {h: 'Un canapé qui ne parle pas à la pièce', t: 'Des lignes arrondies adoucissent. Des lignes droites structurent. Le canapé donne le ton.', img: 'real/B_0'},
  ], end: 'Laquelle faites-vous ? Avouez en commentaire.'},
  {id: 'E_TAILLE', label: 'GUIDE', title: 'La bonne taille\nde table basse', cover: 'AXEL', points: [
    {h: 'Longueur', t: 'Environ 2/3 de la longueur de votre canapé.', img: 'AXEL'},
    {h: 'Distance', t: '40 à 45 cm entre le canapé et la table pour circuler.', img: 'NUAGE'},
    {h: 'Hauteur', t: 'Proche de la hauteur d’assise, autour de 40 à 45 cm.', img: 'ORION'},
    {h: 'Petit salon ?', t: 'Le verre allège visuellement la pièce.', img: 'STELLA'},
  ], end: 'Enregistrez ce guide avant d’acheter.'},
  {id: 'E_SECRET', label: 'LE SECRET', title: 'Pourquoi certains salons\nont l’air plus chers ?', cover: 'real/A_0', points: [
    {h: 'Ce n’est pas le prix des meubles.'},
    {h: 'C’est l’endroit où l’œil se pose.', img: 'real/A_1'},
    {h: 'Le canapé et la table basse sont les premiers points de regard.', img: 'NUAGE'},
    {h: 'Une forme. Une matière. Une harmonie.', img: 'ORION'},
  ], end: 'Partagez à quelqu’un qui refait son salon.'},
  {id: 'E_PETIT', label: 'PETIT SALON', title: '4 règles pour agrandir\nun petit salon', cover: 'STELLA', points: [
    {h: 'Des pieds visibles', t: 'Le sol continue sous les meubles : la pièce respire.', img: 'AXEL'},
    {h: 'Du verre ou des tons clairs', t: 'Ils laissent passer la lumière et le regard.', img: 'STELLA'},
    {h: 'Des formes arrondies', t: 'On circule sans se cogner, l’espace paraît plus fluide.', img: 'NUAGE'},
    {h: 'Un seul point fort', t: 'Une belle pièce vaut mieux que dix objets.', img: 'real/A_1'},
  ], end: 'Enregistrez pour votre prochain aménagement.'},
  {id: 'B_NOMS', label: 'NOYA HOME', title: 'Nos noms\nont un sens', cover: 'real/A_0', points: [
    {h: 'HANA', t: 'La paix, le calme du soir.', img: 'real/A_1'},
    {h: 'LAMMA', t: 'Quand ceux qu’on aime se retrouvent.', img: 'real/B_0'},
    {h: 'SAHRA', t: 'La veillée, le thé, les histoires.', img: 'real/C_0'},
    {h: 'MIDA', t: 'La table où toute la maison se retrouve.', img: 'real/D_0'},
    {h: 'DAR', t: 'La maison où chaque chose a sa place.', img: 'real/E_0'},
  ], end: 'Lequel vous ressemble le plus ?'},
  {id: 'E_BOUCLETTE', label: 'ENTRETIEN', title: 'Bouclette :\nbien l’entretenir', cover: 'real/A_3', points: [
    {h: 'Aspirez régulièrement', t: 'Avec un embout doux, sans appuyer.', img: 'real/A_0'},
    {h: 'Une tache ? Tamponnez', t: 'Ne frottez jamais : vous abîmeriez les boucles.', img: 'real/A_2'},
    {h: 'Évitez le soleil direct', t: 'Une exposition prolongée peut ternir la couleur.', img: 'real/A_4'},
    {h: 'Tapotez les coussins', t: 'Ils gardent leur volume plus longtemps.', img: 'real/A_1'},
  ], end: 'Enregistrez ces conseils.'},
  {id: 'E_QUESTIONS', label: 'AVANT DE COMMANDER', title: '5 questions à poser\navant d’acheter un canapé', cover: 'real/B_0', points: [
    {h: 'Quelles dimensions pour ma pièce ?'},
    {h: 'Quels tissus et quels coloris ?'},
    {h: 'Quel délai de fabrication ?'},
    {h: 'Livrez-vous dans ma wilaya ?', t: 'Chez Noya Home : oui, dans les 69 wilayas.'},
    {h: 'Puis-je payer à la livraison ?', t: 'Chez Noya Home : oui.'},
  ], end: 'Posez-nous les 3 autres en message.'},
  {id: 'E_HANA_TEST', label: 'LE TEST', title: 'HANA est-il fait\npour votre salon ?', cover: 'real/A_1', points: [
    {h: 'Vous aimez les formes arrondies ?'},
    {h: 'Vos murs sont clairs ou neutres ?'},
    {h: 'Le confort passe avant tout ?'},
    {h: 'Vous avez la place pour un canapé et un fauteuil ?'},
    {h: '3 oui sur 4 ?', t: 'HANA est fait pour vous. Envoyez-nous une photo de votre salon, on vous conseille.', img: 'real/A_0'},
  ], end: 'Combien de oui ? Dites-le en commentaire.'},
  {id: 'E_QUIZ', label: 'QUIZ', title: 'Quel salon est fait\npour vous ?', cover: 'real/C_0', points: [
    {h: 'Vous recevez souvent ?', t: 'LAMMA : le salon qui accueille.', img: 'real/B_0'},
    {h: 'Grandes soirées en famille ?', t: 'SAHRA : de la place pour tout le monde.', img: 'real/C_1'},
    {h: 'Envie de calme et de douceur ?', t: 'HANA : le confort avant tout.', img: 'real/A_1'},
  ], end: 'Votre réponse : LAMMA, SAHRA ou HANA ?'},
  {id: 'E_RECEVOIR', label: 'À L’ALGÉRIENNE', title: 'Recevoir\nà l’algérienne', cover: 'real/B_1', points: [
    {h: 'Le café arrive avant les questions.'},
    {h: 'Il faut de la place pour tout le monde.', img: 'real/C_0'},
    {h: 'Une table au centre pour le plateau.', img: 'ORION'},
    {h: 'Et un salon qui dit : marhba bikoum.', img: 'real/B_0'},
  ], end: 'Taguez la personne qui reçoit le mieux.'},
];

export const CHOICES: Choice[] = [
  {id: 'C_HANA', title: 'Votre HANA, vous la voulez en… ?', items: [
    {l: 'A', name: 'Blanc', img: 'real/A_1'}, {l: 'B', name: 'Brun', img: 'real/A_2'}, {l: 'C', name: 'Noir', img: 'real/A_3'}, {l: 'D', name: 'Gris', img: 'real/A_4'}], foot: 'Répondez A, B, C ou D en commentaire'},
  {id: 'C_DROIT_ANGLE', title: 'Canapé droit ou canapé d’angle ?', items: [
    {l: '1', name: 'HANA', img: 'real/A_1'}, {l: '2', name: 'SAHRA', img: 'real/C_0'}], foot: 'Répondez 1 ou 2 en commentaire'},
  {id: 'C_TISSUS', title: 'Quelle teinte pour votre salon ?', items: [
    {l: 'A', name: 'Nuancier 1', img: 'real/G_0'}, {l: 'B', name: 'Nuancier 2', img: 'real/G_1'}], foot: 'Dites-nous votre couleur en commentaire'},
  {id: 'C_LAMMA', title: 'LAMMA : quelle couleur chez vous ?', items: [
    {l: 'A', name: 'Beige', img: 'real/B_0'}, {l: 'B', name: 'Anthracite', img: 'real/B_4'}, {l: 'C', name: 'Bleu roi', img: 'real/B_2'}], foot: 'Répondez A, B ou C en commentaire'},
  {id: 'C_MARBRE_VERRE', title: 'Marbre ou verre ?', items: [
    {l: '1', name: 'ORION', img: 'ORION'}, {l: '2', name: 'AXEL', img: 'AXEL'}], foot: 'Répondez 1 ou 2 en commentaire'},
  {id: 'C_DAR_MIDA', title: 'Vous changez quoi en premier ?', items: [
    {l: '1', name: 'Le salon (DAR)', img: 'real/E_0'}, {l: '2', name: 'La salle à manger (MIDA)', img: 'real/D_0'}], foot: 'Répondez 1 ou 2 en commentaire'},
];
