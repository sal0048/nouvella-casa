// Noya Home — organic-reach carousels built on Sal's real photos (public/noya/real).
// Formula: HOOK → MIRROR → BREAK → REVEAL → PROOF → VARIANTS → soft CTA (save / share / DM).
export type Reach = {
  id: string; meaning: string; hero: string; reveal: string; detail: string; grid: string[]; gridTitle: string;
  hook: string; mirror: string; mirrorSub: string; brk: string; details: string[]; share: string;
};
export const REACH: Reach[] = [
  {
    id: 'HANA', meaning: 'En darija, « el hna » : la paix, le calme.',
    hero: 'A_0', reveal: 'A_1', detail: 'A_3', grid: ['A_1', 'A_2', 'A_3', 'A_4'], gridTitle: 'Blanc, brun, noir ou gris ?',
    hook: 'Vous rentrez épuisé.\nEt votre canapé ne vous accueille pas.',
    mirror: 'Un canapé dur, droit, froid…\nfait pour être regardé.',
    mirrorSub: 'Pas pour s’y poser.',
    brk: 'Le confort ne se voit pas.\nIl se ressent.',
    details: ['Tissu bouclette tout doux', 'Assise capitonnée en boudins arrondis', 'Accoudoirs galbés soulignés de bois'],
    share: 'quelqu’un qui mérite un vrai repos',
  },
  {
    id: 'LAMMA', meaning: 'La lamma : quand ceux qu’on aime se retrouvent.',
    hero: 'B_1', reveal: 'B_0', detail: 'B_2', grid: ['B_0', 'B_2', 'B_4', 'B_3'], gridTitle: 'Beige, bleu, anthracite… choisissez.',
    hook: 'Les invités arrivent dans 10 minutes.\nVotre salon est prêt ?',
    mirror: 'La lamma du vendredi, les fêtes, les visites…\net un salon qui ne suit pas.',
    mirrorSub: 'Recevoir devient un stress.',
    brk: 'Recevoir, ce n’est pas avoir plus de places.\nC’est avoir un salon qui accueille.',
    details: ['Dossier généreux et accoudoirs larges', 'Finitions en bois galbé', 'Plusieurs coloris disponibles'],
    share: 'la personne qui reçoit toute la famille',
  },
  {
    id: 'SAHRA', meaning: 'La sahra : la veillée, le thé, les histoires.',
    hero: 'C_0', reveal: 'C_1', detail: 'C_0', grid: ['C_0', 'C_1'], gridTitle: 'De la place pour toute la famille',
    hook: 'Il est minuit.\nPersonne ne veut rentrer.',
    mirror: 'Les soirées en famille\noù il manque toujours une place…',
    mirrorSub: 'Quelqu’un finit toujours sur une chaise.',
    brk: 'Une grande famille n’a pas besoin\nd’un grand salon.\nElle a besoin d’un angle.',
    details: ['Canapé d’angle grand format', 'Coussins de dossier moelleux', 'Plusieurs tissus et coloris'],
    share: 'votre partenaire de veillées',
  },
  {
    id: 'MIDA', meaning: 'La mida : la table où toute la maison se retrouve.',
    hero: 'D_0', reveal: 'D_1', detail: 'D_0', grid: ['D_0', 'D_1'], gridTitle: 'Verre, bois et assises enveloppantes',
    hook: 'Quand avez-vous mangé tous ensemble\npour la dernière fois ?',
    mirror: 'Chacun son assiette,\nchacun son téléphone…',
    mirrorSub: 'La maison est pleine, la table est vide.',
    brk: 'Une table ne sert pas qu’à manger.\nElle rassemble.',
    details: ['Plateau en verre', 'Chaises en bois au dossier enveloppant', 'Assise rembourrée'],
    share: 'celui ou celle qui rassemble la famille',
  },
  {
    id: 'DAR', meaning: 'Dar : la maison où chaque chose a sa place.',
    hero: 'E_1', reveal: 'E_0', detail: 'E_2', grid: ['E_0', 'E_1', 'E_2', 'E_3'], gridTitle: 'Meuble TV, buffet, vitrine, table basse',
    hook: 'Votre salon est rangé…\nmais il ne fait pas « maison ».',
    mirror: 'Des affaires partout,\nrien n’a vraiment sa place.',
    mirrorSub: 'Et l’œil ne se repose jamais.',
    brk: 'Une maison apaisée commence\npar des rangements bien pensés.',
    details: ['Meuble TV, buffet et vitrine assortis', 'Bois clair aux formes arrondies', 'Portes et tiroirs de rangement'],
    share: 'quelqu’un qui emménage bientôt',
  },
];
