# quest.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class Quest:
    """
    Représente une quête du jeu.

    Une quête est définie par :
    - un identifiant (qid)
    - un titre + une description
    - une liste d'objectifs (strings)
    - une liste de récompenses (texte, ou plus tard des items/XP si tu veux)

    La quête peut être :
    - inactive (pas encore suivie)
    - active (en cours)
    - terminée (complétée)
    """
    qid: str
    title: str
    description: str
    objectives: List[str]
    reward: List[str] = field(default_factory=list)

    active: bool = False
    completed: bool = False
    objectives_done: Set[str] = field(default_factory=set)

    def activate(self) -> None:
        """Active la quête (si elle n'est pas déjà terminée)."""
        if self.completed:
            return
        self.active = True

    def is_active(self) -> bool:
        """Renvoie True si la quête est en cours (active et non terminée)."""
        return self.active and not self.completed

    def progress(self) -> str:
        """Retourne un résumé simple de la progression, ex: '2/6'."""
        return f"{len(self.objectives_done)}/{len(self.objectives)}"

    def status_line(self) -> str:
        """Une ligne courte affichable dans la liste des quêtes."""
        if self.completed:
            state = "✅ TERMINÉE"
        elif self.active:
            state = "🟡 ACTIVE"
        else:
            state = "⚪ INACTIVE"
        return f"[{self.qid}] {self.title} — {state} ({self.progress()})"

    def details(self) -> str:
        """Retourne un affichage détaillé (objectifs + récompenses)."""
        lines: List[str] = [self.status_line(), self.description, "", "Objectifs :"]
        for obj in self.objectives:
            mark = "✅" if obj in self.objectives_done else "⬜"
            lines.append(f"  {mark} {obj}")

        if self.reward:
            lines += ["", "Récompenses :"]
            for r in self.reward:
                lines.append(f"  🎁 {r}")

        return "\n".join(lines)

    def complete_objective(self, objective: str) -> bool:
        """
        Valide un objectif (string exact) si la quête est active.

        Retourne True si ça a effectivement changé quelque chose
        (évite de spammer les logs quand on valide deux fois la même chose).
        """
        if self.completed or not self.active:
            return False
        if objective not in self.objectives:
            return False
        if objective in self.objectives_done:
            return False

        self.objectives_done.add(objective)

        if self._is_finished():
            self._finish()

        return True

    def _is_finished(self) -> bool:
        """Vrai si tous les objectifs de la quête sont validés."""
        return len(self.objectives_done) >= len(self.objectives)

    def _finish(self) -> None:
        """Passe la quête en 'terminée' et la désactive."""
        self.completed = True
        self.active = False


class QuestManager:
    """
    Gère l'ensemble des quêtes du jeu.

    Rôle :
    - enregistrer les quêtes
    - activer une quête "suivie"
    - valider des objectifs
    - conserver un petit journal (log) à afficher dans l'interface
    """
    def __init__(self):
        self.quests: Dict[str, Quest] = {}
        self.active_qid: Optional[str] = None
        self._log: List[str] = []

    def add_quest(self, quest: Quest) -> None:
        """Ajoute (ou remplace) une quête dans le registre."""
        self.quests[quest.qid] = quest

    def get(self, qid: str) -> Optional[Quest]:
        """Récupère une quête par son id."""
        return self.quests.get(qid)

    def list_quests(self) -> str:
        """Affiche la liste des quêtes avec leur statut."""
        if not self.quests:
            return "\n(Aucune quête)\n"

        lines = ["\n=== QUÊTES ==="]
        for q in self.quests.values():
            lines.append(q.status_line())
        lines.append("")
        lines.append("Commandes : quests | quest <id> | activate <id> | rewards")
        return "\n".join(lines) + "\n"

    def quest_details(self, qid: str) -> str:
        """Affiche une quête en détail (objectifs + récompenses)."""
        q = self.get(qid)
        if not q:
            return "\nQuête introuvable.\n"
        return "\n" + q.details() + "\n"

    def activate(self, qid: str) -> bool:
        """Active une quête et la définit comme quête suivie."""
        q = self.get(qid)
        if not q:
            return False

        q.activate()
        self.active_qid = qid
        self._push_log(f"🟡 Quête activée : {q.title} ({qid})")
        return True

    def rewards(self) -> str:
        """Affiche les récompenses des quêtes terminées."""
        lines = ["\n=== RÉCOMPENSES (quêtes terminées) ==="]
        any_reward = False

        for q in self.quests.values():
            if q.completed and q.reward:
                any_reward = True
                lines.append(f"- {q.title} [{q.qid}]")
                for r in q.reward:
                    lines.append(f"  🎁 {r}")

        if not any_reward:
            lines.append("(Aucune récompense pour l’instant)")

        return "\n".join(lines) + "\n"

    def complete(self, qid: str, objective: str) -> bool:
        """
        Valide un objectif sur une quête précise.

        Retourne True si l'objectif a été validé pour de vrai.
        """
        q = self.get(qid)
        if not q:
            return False

        changed = q.complete_objective(objective)
        if changed:
            self._push_log(f"✅ Objectif validé [{qid}] : {objective}")
            if q.completed:
                self._push_log(f"🏁 Quête terminée [{qid}] : {q.title}")

        return changed

    def complete_on_active(self, objective: str) -> bool:
        """Valide un objectif sur la quête suivie (si elle existe)."""
        if not self.active_qid:
            return False
        return self.complete(self.active_qid, objective)

    def pop_updates(self) -> List[str]:
        """Renvoie les messages du journal puis vide le buffer."""
        out = self._log[:]
        self._log.clear()
        return out

    def on_event(self, event_type: str, payload: Any = None) -> None:
        """
        Point d'entrée si tu veux un jour automatiser la validation d'objectifs.

        Exemple :
        - event_type="ENTER_ROOM", payload="No Man’s Land"
        - event_type="TAKE_ITEM", payload="Envelope_Orders"

        Pour l'instant, ton jeu est très narratif :
        c'est plus simple et plus clair de déclencher complete() directement
        au bon endroit dans game.py.
        """
        return

    def _push_log(self, msg: str) -> None:
        """Ajoute un message au journal (affiché ensuite par le jeu)."""
        self._log.append(msg)
