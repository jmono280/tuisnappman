from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static


class ConfirmScreen(ModalScreen[bool]):
    """Confirmación de acciones destructivas: muestra el comando exacto."""

    BINDINGS = [("escape", "cancel", "Cancelar")]

    def __init__(self, title: str, command: str, detail: str = "") -> None:
        super().__init__()
        self._title = title
        self._command = command
        self._detail = detail

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Label(self._title, classes="dialog-title")
            if self._detail:
                yield Static(self._detail, markup=False)
            yield Static(f"$ {self._command}", classes="command", markup=False)
            with Horizontal(classes="buttons"):
                yield Button("Cancelar", id="cancel", variant="primary")
                yield Button("Confirmar", id="ok", variant="error")

    def on_mount(self) -> None:
        self.query_one("#cancel", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "ok")

    def action_cancel(self) -> None:
        self.dismiss(False)


class PromptScreen(ModalScreen[str | None]):
    """Pide un texto (descripción del snapshot)."""

    BINDINGS = [("escape", "cancel", "Cancelar")]

    def __init__(self, title: str, placeholder: str = "") -> None:
        super().__init__()
        self._title = title
        self._placeholder = placeholder

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Label(self._title, classes="dialog-title")
            yield Input(placeholder=self._placeholder)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        self.dismiss(text or None)

    def action_cancel(self) -> None:
        self.dismiss(None)
