// Noya Home — French carousel copy. Facts come from the Airtable catalog (🪑 كتالوج الموديلات).
// No prices on slides (price is given in DM), no invented scarcity or discounts.
export type Model = {
  id: string; img: string; sibling: string; family: string;
  hook: string; problem: string; problemSub: string;
  tagline: string; details: string[]; why: string[];
  faq: [string, string][]; teaser: string; teaserSub: string;
  finishes: string; delay: string;
};

export const MODELS: Model[] = [
  {
    id: 'ORION', img: 'ORION.jpg', sibling: 'NUAGE', family: 'Collection Pierre & Hêtre',
    hook: 'Ce salon a un secret.\nIl tient en deux tables.',
    problem: 'Un salon déjà meublé…\nmais qui ressemble à tous les autres.',
    problemSub: 'Tout est là. Rien ne dit : « c’est chez moi ».',
    tagline: 'Deux tables gigognes. Une pierre. Un pied sculpté.',
    details: ['Plateaux Ø70 et Ø50 cm', 'Marbre naturel ou porcelaine', 'Bases cylindriques en hêtre cannelé'],
    why: ['Chaque plateau en marbre est unique, avec ses propres veines', 'Deux pièces séparées : décalez-les, combinez-les', 'Le hêtre cannelé, façonné comme une colonne'],
    faq: [['Le marbre, difficile à entretenir ?', 'Surface traitée : un simple chiffon suffit.'], ['Marbre ou porcelaine ?', 'Le marbre est unique par ses veines. La porcelaine est plus légère et facile à vivre.']],
    teaser: 'ORION a un frère.', teaserSub: 'Même hêtre. Même pierre. Zéro angle.\nDécouvrez-le dans le prochain post.',
    finishes: 'Marbre ou porcelaine', delay: '3 à 7 jours',
  },
  {
    id: 'NUAGE', img: 'NUAGE.jpg', sibling: 'ORION', family: 'Collection Pierre & Hêtre',
    hook: 'Pas un seul angle.\nEt ce n’est pas un hasard.',
    problem: 'Des coins pointus…\net une maman qui surveille chaque pas des enfants.',
    problemSub: 'La table qui devait réunir la famille devient un souci.',
    tagline: 'Une forme de nuage, posée sur deux colonnes de hêtre.',
    details: ['Plateau 110 × 60 cm', 'Marbre naturel ou porcelaine', 'Deux bases en hêtre massif cannelé', 'Existe avec sa table d’appoint'],
    why: ['Zéro angle vif : une forme organique pensée pour la famille', 'Pierre naturelle polie, pas de résine ni de vinyle', 'Hêtre massif sculpté, pas de MDF plaqué'],
    faq: [['Les bords s’abîment ?', 'Bords arrondis et polis : rien ne s’écaille.'], ['Elle ira avec mon salon ?', 'Envoyez-nous une photo de votre salon, on vous montre le rendu.']],
    teaser: 'Son frère, c’est ORION.', teaserSub: 'Deux tables rondes, la même famille.\nÀ voir dans le post précédent.',
    finishes: 'Marbre ou porcelaine', delay: '7 jours',
  },
  {
    id: 'AXEL', img: 'AXEL.jpg', sibling: 'ATLAS', family: 'Collection Verre & Hêtre',
    hook: 'Votre salon étouffe ?\nLe problème n’est pas sa taille.',
    problem: 'Des meubles lourds\nqui mangent tout l’espace.',
    problemSub: 'L’œil ne se repose jamais.',
    tagline: 'Un verre qui semble flotter sur un X de hêtre.',
    details: ['100 × 60 cm, hauteur 45 cm', 'Verre trempé', 'Pieds en X en hêtre massif'],
    why: ['Le verre laisse voir la structure : légèreté visuelle', 'Croisement aux extrémités : le centre reste libre', 'Hêtre massif, fait pour durer'],
    faq: [['Le verre, ça casse ?', 'Verre trempé, conçu pour un usage quotidien.'], ['Les pieds en X gênent ?', 'Le croisement est aux extrémités : plus de place qu’une table à 4 pieds.']],
    teaser: 'AXEL a un frère plus audacieux.', teaserSub: 'Celui que vos invités remarquent en premier.\nDécouvrez-le dans le prochain post.',
    finishes: 'Hêtre clair ou cerisier sombre', delay: '3 à 7 jours',
  },
  {
    id: 'ATLAS', img: 'ATLAS.jpg', sibling: 'AXEL', family: 'Collection Verre & Hêtre',
    hook: '« Vous l’avez trouvée où ? »\nLa question que vos invités vont poser.',
    problem: 'Un salon correct, propre…\nmais que personne ne remarque.',
    problemSub: 'Il manque une pièce qui attire le regard.',
    tagline: 'Comme le titan qui porte le ciel, sa structure porte le verre.',
    details: ['100 × 60 cm, hauteur 45 cm', 'Verre trempé', 'Piètement sculpté en hêtre massif'],
    why: ['Un assemblage central travaillé à la main', 'Chaque angle offre une vue différente', 'Une structure que peu d’artisans maîtrisent'],
    faq: [['Le verre est stable ?', 'Verre trempé posé sur des appuis équilibrés.'], ['Trop audacieuse ?', 'C’est justement elle qu’on remarque.']],
    teaser: 'Son frère, c’est AXEL.', teaserSub: 'Même hêtre, des lignes plus calmes.\nÀ voir dans le post précédent.',
    finishes: 'Hêtre clair ou cerisier sombre', delay: '3 à 7 jours',
  },
  {
    id: 'ARC', img: 'ARC.jpg', sibling: 'STELLA', family: 'Collection Courbes',
    hook: 'Le soir, chacun dans son coin.\nEt si c’était la faute de la table ?',
    problem: 'Un salon où la famille\nne se réunit plus.',
    problemSub: 'La table reste froide. Et vide.',
    tagline: 'Un piètement en arc, sculpté dans le hêtre.',
    details: ['100 × 60 ou 110 × 60 cm, hauteur 45 cm', 'Verre trempé', 'Hêtre massif 100 %, sans MDF'],
    why: ['Hêtre massif, pas de MDF', 'Fabriquée à la main, sur commande', 'Photos réelles de votre pièce avant la livraison'],
    faq: [['C’est un investissement ?', 'Une pièce qui traverse les modes et rassemble la famille.'], ['Le verre avec des enfants ?', 'Verre trempé sécurisé, pensé pour la vie de famille.']],
    teaser: 'ARC a un petit frère.', teaserSub: 'Carré, léger, en forme d’étoile.\nDécouvrez-le dans le prochain post.',
    finishes: 'Hêtre clair ou cerisier sombre', delay: '3 à 7 jours',
  },
  {
    id: 'STELLA', img: 'STELLA.jpg', sibling: 'ARC', family: 'Collection Courbes',
    hook: '4 pieds. 1 étoile.\n0 encombrement.',
    problem: 'Un petit salon\noù chaque meuble de trop se voit.',
    problemSub: 'Il faut de la présence, sans le poids.',
    tagline: 'Quatre pieds courbés en hêtre qui se rejoignent au centre.',
    details: ['80 × 80 cm, hauteur 45 cm', 'Verre trempé', 'Hêtre massif'],
    why: ['Le verre carré semble flotter', 'Un design léger qui agrandit la pièce', 'Pieds ouverts jusqu’aux bords : stabilité totale'],
    faq: [['Le verre, ça casse ?', 'Verre trempé, conçu pour le quotidien.'], ['Elle est stable ?', 'Les 4 pieds s’ouvrent jusqu’aux bords du verre.']],
    teaser: 'Son grand frère, c’est ARC.', teaserSub: 'Même hêtre, format rectangulaire.\nÀ voir dans le post précédent.',
    finishes: 'Hêtre clair ou cerisier sombre', delay: '3 à 7 jours',
  },
];
export const SLIDES = 8;
