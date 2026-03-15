"""Session and memory cleaner for nanobot.

Provides interactive cleaning functionality for session files and memory files.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


class SessionCleaner:
    """Interactive cleaner for session and memory files."""

    def __init__(self, workspace: Path):
        """
        Initialize the session cleaner.

        Args:
            workspace: Path to the nanobot workspace directory.
        """
        self.workspace = workspace
        self.sessions_dir = workspace / "sessions"
        self.memory_dir = workspace / "memory"

    def run(self) -> None:
        """Run the interactive cleaner main menu."""
        while True:
            console.clear()
            console.print(Panel.fit(
                "[bold cyan]nanobot Session Cleaner[/bold cyan]\n"
                "清理session历史和memory文件，减少token消耗",
                title="🐈 nanobot",
            ))

            table = Table(show_header=False, box=None)
            table.add_column("Option", style="cyan")
            table.add_column("Description")
            table.add_row("1", "清理 Session 文件 (按文件删除)")
            table.add_row("2", "清理 Session 内容 (按消息行删除)")
            table.add_row("3", "清理 Memory 文件 (按文件删除)")
            table.add_row("4", "查看 Session 统计信息")
            table.add_row("q", "退出")
            console.print(table)
            console.print()

            choice = prompt(HTML("<b>请选择操作 [1-4/q]: </b>")).strip().lower()

            if choice == "1":
                self._clean_session_files()
            elif choice == "2":
                self._clean_session_content()
            elif choice == "3":
                self._clean_memory_files()
            elif choice == "4":
                self._show_session_stats()
            elif choice in ("q", "quit", "exit"):
                console.print("[green]再见！[/green]")
                break
            else:
                console.print("[red]无效选择，请重试[/red]")

            if choice in ("1", "2", "3", "4"):
                prompt(HTML("<dim>按 Enter 继续...</dim>"))

    def _list_sessions(self) -> list[dict[str, Any]]:
        """
        List all session files with metadata.

        Returns:
            List of session info dictionaries.
        """
        sessions = []
        if not self.sessions_dir.exists():
            return sessions

        for path in sorted(self.sessions_dir.glob("*.jsonl")):
            try:
                info = self._parse_session_file(path)
                info["path"] = path
                sessions.append(info)
            except Exception as e:
                sessions.append({
                    "path": path,
                    "key": path.stem,
                    "error": str(e),
                    "messages": 0,
                    "created_at": None,
                    "updated_at": None,
                })

        return sessions

    def _parse_session_file(self, path: Path) -> dict[str, Any]:
        """
        Parse a session JSONL file and extract metadata.

        Args:
            path: Path to the session file.

        Returns:
            Dictionary with session metadata.
        """
        metadata = {}
        message_count = 0
        created_at = None
        updated_at = None

        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    if data.get("_type") == "metadata":
                        metadata = data
                        created_at = data.get("created_at")
                        updated_at = data.get("updated_at")
                    else:
                        message_count += 1
                except json.JSONDecodeError:
                    message_count += 1

        return {
            "key": metadata.get("key", path.stem),
            "messages": message_count,
            "created_at": created_at,
            "updated_at": updated_at,
            "metadata": metadata,
        }

    def _format_datetime(self, dt_str: str | None) -> str:
        """Format ISO datetime string for display."""
        if not dt_str:
            return "-"
        try:
            dt = datetime.fromisoformat(dt_str)
            return dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return dt_str

    def _estimate_tokens(self, message_count: int) -> str:
        """Estimate token count based on message count."""
        estimated = message_count * 500
        if estimated > 1000000:
            return f"~{estimated // 1000000}M"
        elif estimated > 1000:
            return f"~{estimated // 1000}K"
        return f"~{estimated}"

    def _clean_session_files(self) -> None:
        """Interactive session file deletion."""
        sessions = self._list_sessions()

        if not sessions:
            console.print("[yellow]没有找到任何 session 文件[/yellow]")
            return

        console.print("\n[bold]Session 文件列表:[/bold]\n")

        table = Table()
        table.add_column("#", style="dim")
        table.add_column("Session Key", style="cyan")
        table.add_column("消息数")
        table.add_column("估算Token")
        table.add_column("创建时间")
        table.add_column("更新时间")

        for i, s in enumerate(sessions, 1):
            table.add_row(
                str(i),
                s.get("key", s["path"].stem),
                str(s.get("messages", 0)),
                self._estimate_tokens(s.get("messages", 0)),
                self._format_datetime(s.get("created_at")),
                self._format_datetime(s.get("updated_at")),
            )

        console.print(table)
        console.print()

        console.print("[dim]输入要删除的 session 编号（多个用逗号分隔，如 1,3,5），或输入 'all' 删除全部，'q' 取消[/dim]")
        choice = prompt(HTML("<b>选择: </b>")).strip().lower()

        if choice == "q" or not choice:
            console.print("[yellow]已取消[/yellow]")
            return

        to_delete = []
        if choice == "all":
            to_delete = [s["path"] for s in sessions]
        else:
            try:
                indices = [int(x.strip()) for x in choice.split(",")]
                for idx in indices:
                    if 1 <= idx <= len(sessions):
                        to_delete.append(sessions[idx - 1]["path"])
                    else:
                        console.print(f"[red]无效编号: {idx}[/red]")
            except ValueError:
                console.print("[red]无效输入[/red]")
                return

        if not to_delete:
            console.print("[yellow]没有选择任何文件[/yellow]")
            return

        console.print(f"\n[bold]将删除以下 {len(to_delete)} 个 session 文件:[/bold]")
        for p in to_delete:
            console.print(f"  - {p.name}")

        confirm = prompt(HTML("<b>确认删除? [y/N]: </b>")).strip().lower()
        if confirm == "y":
            for p in to_delete:
                p.unlink()
                console.print(f"[green]✓[/green] 已删除: {p.name}")
            console.print(f"[green]完成！删除了 {len(to_delete)} 个文件[/green]")
        else:
            console.print("[yellow]已取消[/yellow]")

    def _clean_session_content(self) -> None:
        """Interactive session content line-by-line deletion."""
        sessions = self._list_sessions()

        if not sessions:
            console.print("[yellow]没有找到任何 session 文件[/yellow]")
            return

        console.print("\n[bold]选择要清理的 Session:[/bold]\n")

        for i, s in enumerate(sessions, 1):
            console.print(f"  [cyan]{i}[/cyan]. {s.get('key', s['path'].stem)} ({s.get('messages', 0)} 条消息)")

        console.print()
        choice = prompt(HTML("<b>选择 session 编号 [q 取消]: </b>")).strip().lower()

        if choice == "q" or not choice:
            console.print("[yellow]已取消[/yellow]")
            return

        try:
            idx = int(choice)
            if not 1 <= idx <= len(sessions):
                console.print("[red]无效编号[/red]")
                return
        except ValueError:
            console.print("[red]无效输入[/red]")
            return

        session_path = sessions[idx - 1]["path"]
        self._edit_session_lines(session_path)

    def _edit_session_lines(self, session_path: Path) -> None:
        """
        Edit session file line by line.

        Args:
            session_path: Path to the session file.
        """
        lines = []
        with open(session_path, encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if line:
                    lines.append((i + 1, line))

        if len(lines) <= 1:
            console.print("[yellow]Session 文件为空或只有元数据[/yellow]")
            return

        console.print(f"\n[bold]Session: {session_path.name}[/bold]")
        console.print(f"[dim]共 {len(lines)} 行，显示前 50 行[/dim]\n")

        table = Table()
        table.add_column("行号", style="dim", width=6)
        table.add_column("类型", width=10)
        table.add_column("内容预览")

        display_lines = lines[:50]
        for line_num, line_content in display_lines:
            try:
                data = json.loads(line_content)
                if data.get("_type") == "metadata":
                    row_type = "[dim]metadata[/dim]"
                    preview = f"key: {data.get('key', '-')}"
                else:
                    role = data.get("role", "?")
                    row_type = f"[cyan]{role}[/cyan]"
                    content = data.get("content", "")
                    if isinstance(content, str):
                        preview = content[:80] + ("..." if len(content) > 80 else "")
                    elif isinstance(content, list):
                        preview = f"[多部分内容, {len(content)} 项]"
                    else:
                        preview = str(content)[:80]

                    if data.get("tool_calls"):
                        preview = f"[工具调用] {data['tool_calls'][0].get('function', {}).get('name', '?')}"
                    if data.get("name"):
                        preview = f"[{data.get('name')}] {preview[:50]}"

                table.add_row(str(line_num), row_type, preview)
            except json.JSONDecodeError:
                table.add_row(str(line_num), "[red]error[/red]", line_content[:80])

        console.print(table)

        if len(lines) > 50:
            console.print(f"\n[dim]... 还有 {len(lines) - 50} 行未显示[/dim]")

        console.print("\n[bold]删除选项:[/bold]")
        console.print("  [cyan]range[/cyan] - 按行号范围删除 (如: 5-20)")
        console.print("  [cyan]role[/cyan]  - 按角色类型删除 (如: tool, user, assistant)")
        console.print("  [cyan]keep[/cyan]  - 保留指定行号，删除其他")
        console.print("  [cyan]q[/cyan]     - 取消")

        action = prompt(HTML("<b>选择操作: </b>")).strip().lower()

        if action == "q" or not action:
            console.print("[yellow]已取消[/yellow]")
            return

        lines_to_keep = self._select_lines_to_keep(action, lines)

        if lines_to_keep is None:
            return

        if len(lines_to_keep) == len(lines):
            console.print("[yellow]没有行被标记删除[/yellow]")
            return

        removed_count = len(lines) - len(lines_to_keep)
        console.print(f"\n[bold]将删除 {removed_count} 行，保留 {len(lines_to_keep)} 行[/bold]")

        confirm = prompt(HTML("<b>确认删除? [y/N]: </b>")).strip().lower()
        if confirm == "y":
            with open(session_path, "w", encoding="utf-8") as f:
                for _, line_content in lines_to_keep:
                    f.write(line_content + "\n")
            console.print(f"[green]✓ 已删除 {removed_count} 行[/green]")
        else:
            console.print("[yellow]已取消[/yellow]")

    def _select_lines_to_keep(self, action: str, lines: list[tuple[int, str]]) -> list[tuple[int, str]] | None:
        """
        Select which lines to keep based on action.

        Args:
            action: The action type (range, role, keep).
            lines: List of (line_number, content) tuples.

        Returns:
            List of lines to keep, or None if cancelled.
        """
        if action == "range":
            range_input = prompt(HTML("<b>输入行号范围 (如 5-20): </b>")).strip()
            try:
                if "-" in range_input:
                    start, end = map(int, range_input.split("-"))
                else:
                    start = end = int(range_input)

                to_remove = set(range(start, end + 1))
                return [(n, c) for n, c in lines if n not in to_remove]
            except ValueError:
                console.print("[red]无效的范围格式[/red]")
                return None

        elif action == "role":
            role_input = prompt(HTML("<b>输入要删除的角色类型 (tool/user/assistant): </b>")).strip().lower()
            valid_roles = {"tool", "user", "assistant"}
            if role_input not in valid_roles:
                console.print(f"[red]无效角色类型，可选: {', '.join(valid_roles)}[/red]")
                return None

            result = []
            for line_num, line_content in lines:
                try:
                    data = json.loads(line_content)
                    if data.get("_type") == "metadata":
                        result.append((line_num, line_content))
                    elif data.get("role") != role_input:
                        result.append((line_num, line_content))
                except json.JSONDecodeError:
                    result.append((line_num, line_content))

            return result

        elif action == "keep":
            keep_input = prompt(HTML("<b>输入要保留的行号 (逗号分隔，如 1,2,3): </b>")).strip()
            try:
                keep_nums = set(int(x.strip()) for x in keep_input.split(","))
                return [(n, c) for n, c in lines if n in keep_nums]
            except ValueError:
                console.print("[red]无效的行号格式[/red]")
                return None

        else:
            console.print("[red]未知操作[/red]")
            return None

    def _clean_memory_files(self) -> None:
        """Interactive memory file deletion."""
        if not self.memory_dir.exists():
            console.print("[yellow]Memory 目录不存在[/yellow]")
            return

        files = list(self.memory_dir.glob("*"))
        files = [f for f in files if f.is_file()]

        if not files:
            console.print("[yellow]没有找到任何 memory 文件[/yellow]")
            return

        console.print("\n[bold]Memory 文件列表:[/bold]\n")

        table = Table()
        table.add_column("#", style="dim")
        table.add_column("文件名", style="cyan")
        table.add_column("大小")
        table.add_column("修改时间")

        for i, f in enumerate(files, 1):
            stat = f.stat()
            size = self._format_size(stat.st_size)
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
            table.add_row(str(i), f.name, size, mtime)

        console.print(table)
        console.print()

        console.print("[dim]输入要删除的文件编号（多个用逗号分隔），或 'all' 删除全部，'q' 取消[/dim]")
        choice = prompt(HTML("<b>选择: </b>")).strip().lower()

        if choice == "q" or not choice:
            console.print("[yellow]已取消[/yellow]")
            return

        to_delete = []
        if choice == "all":
            to_delete = files
        else:
            try:
                indices = [int(x.strip()) for x in choice.split(",")]
                for idx in indices:
                    if 1 <= idx <= len(files):
                        to_delete.append(files[idx - 1])
                    else:
                        console.print(f"[red]无效编号: {idx}[/red]")
            except ValueError:
                console.print("[red]无效输入[/red]")
                return

        if not to_delete:
            console.print("[yellow]没有选择任何文件[/yellow]")
            return

        console.print(f"\n[bold]将删除以下 {len(to_delete)} 个文件:[/bold]")
        for f in to_delete:
            console.print(f"  - {f.name}")

        confirm = prompt(HTML("<b>确认删除? [y/N]: </b>")).strip().lower()
        if confirm == "y":
            for f in to_delete:
                f.unlink()
                console.print(f"[green]✓[/green] 已删除: {f.name}")
            console.print(f"[green]完成！删除了 {len(to_delete)} 个文件[/green]")
        else:
            console.print("[yellow]已取消[/yellow]")

    def _format_size(self, size: int) -> str:
        """Format file size for display."""
        if size > 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        elif size > 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size} B"

    def _show_session_stats(self) -> None:
        """Show session statistics."""
        sessions = self._list_sessions()

        if not sessions:
            console.print("[yellow]没有找到任何 session 文件[/yellow]")
            return

        total_messages = sum(s.get("messages", 0) for s in sessions)
        total_tokens = self._estimate_tokens(total_messages)

        console.print("\n[bold]Session 统计信息:[/bold]\n")

        table = Table()
        table.add_column("统计项", style="cyan")
        table.add_column("值")
        table.add_row("Session 文件数", str(len(sessions)))
        table.add_row("总消息数", str(total_messages))
        table.add_row("估算总Token", total_tokens)

        console.print(table)

        console.print("\n[bold]各 Session 详情:[/bold]\n")

        detail_table = Table()
        detail_table.add_column("Session Key", style="cyan")
        detail_table.add_column("消息数")
        detail_table.add_column("估算Token")
        detail_table.add_column("文件大小")

        for s in sessions:
            path = s.get("path")
            size = self._format_size(path.stat().st_size) if path and path.exists() else "-"
            detail_table.add_row(
                s.get("key", "-"),
                str(s.get("messages", 0)),
                self._estimate_tokens(s.get("messages", 0)),
                size,
            )

        console.print(detail_table)


def run_cleaner(workspace: Path) -> None:
    """
    Run the session cleaner interactively.

    Args:
        workspace: Path to the nanobot workspace directory.
    """
    cleaner = SessionCleaner(workspace)
    cleaner.run()
