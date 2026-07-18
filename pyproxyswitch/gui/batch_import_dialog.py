#!/usr/bin/env python

"""
批量导入对话框模块

提供批量导入/导出代理的功能，从 config_dialog.py 中抽取。
"""


from collections.abc import Sequence

from PySide6 import QtCore, QtWidgets

from pyproxyswitch.proxy_list import format_proxy
from pyproxyswitch.proxy_validation import (
    BatchImportValidator,
    ValidatedProxy,
    ValidationError,
)


class BatchImportDialog(QtWidgets.QDialog):
    """批量导入代理对话框"""

    def __init__(
        self, parent: QtWidgets.QWidget | None = None, initial_content: str = ""
    ) -> None:
        """初始化对话框

        Args:
            parent: 父窗口
            initial_content: 初始内容（用于编辑现有代理列表）
        """
        super().__init__(parent)
        self._validator = BatchImportValidator()
        self._valid_proxies: list[ValidatedProxy] = []

        self._setup_ui(initial_content)

    def _setup_ui(self, initial_content: str) -> None:
        """设置UI"""
        self.resize(600, 400)
        self.setModal(True)
        self.setWindowTitle(self.tr("Batch Add/Modify/Delete Proxy"))

        # 创建提示信息
        lbl_text = self.tr(
            'Please use the following syntax for one proxy per line:\n\n'
            'proxy_name address:port username:password proxy_type\n\n'
            '"username" and "password" are only required when the proxy needs '
            'authorization.\n'
            '"proxy_type" can be HTTP, SOCKS4 or SOCKS5.\n\n'
            'Example:\n'
            'my_proxy 192.168.1.100:8080\n'
            'auth_proxy 10.0.0.1:3120 user:pass HTTP\n'
            'socks_proxy 203.0.113.5:1080 SOCKS5\n\n'
        )

        self._lbl_tip = QtWidgets.QLabel(lbl_text, self)
        self._lbl_tip.setWordWrap(True)
        self._lbl_tip.setIndent(2)

        # 创建错误信息显示区域
        self._lbl_error = QtWidgets.QLabel(self)
        self._lbl_error.setStyleSheet("color: red;")
        self._lbl_error.setWordWrap(True)
        self._lbl_error.hide()

        # 创建文本编辑器
        self._txt_editor = QtWidgets.QPlainTextEdit(initial_content, self)

        # 添加预览按钮
        self._btn_preview = QtWidgets.QPushButton(self.tr("Preview"))
        self._btn_preview.clicked.connect(self._on_preview)

        # 创建按钮盒
        self._btn_box = QtWidgets.QDialogButtonBox(self)
        self._btn_box.setStandardButtons(
            QtWidgets.QDialogButtonBox.StandardButton.Cancel |
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        )
        self._btn_box.accepted.connect(self._on_accept)
        self._btn_box.rejected.connect(self.reject)

        # 设置布局
        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self._lbl_tip, 0, 0, 1, 2)
        layout.addWidget(self._txt_editor, 1, 0, 1, 2)
        layout.addWidget(self._lbl_error, 2, 0, 1, 2)
        layout.addWidget(self._btn_preview, 3, 0)
        layout.addWidget(self._btn_box, 3, 1)
        self.setLayout(layout)

    def _on_preview(self) -> None:
        """预览按钮点击处理"""
        self._lbl_error.hide()

        try:
            valid_proxies = self._validator.validate_batch_content(
                self._txt_editor.toPlainText()
            )

            # 显示预览信息
            preview_text = self.tr("Valid proxies found:")
            preview_text += "\n\n"
            for i, proxy in enumerate(valid_proxies[:10], 1):
                preview_text += f"{i}. {proxy[0]} - {proxy[1]}:{proxy[2]} ({proxy[3]})\n"

            if len(valid_proxies) > 10:
                preview_text += "\n... and " + str(len(valid_proxies) - 10) + " " + self.tr("more")

            QtWidgets.QMessageBox.information(
                self,
                self.tr("Import Preview"),
                preview_text,
                QtWidgets.QMessageBox.StandardButton.Ok
            )

        except ValidationError as e:
            self._lbl_error.setText(str(e))
            self._lbl_error.show()
        except Exception as e:
            self._lbl_error.setText(str(e))
            self._lbl_error.show()

    def _on_accept(self) -> None:
        """确认按钮点击处理"""
        try:
            valid_proxies = self._validator.validate_batch_content(
                self._txt_editor.toPlainText()
            )

            if not valid_proxies:
                QtWidgets.QMessageBox.warning(
                    self,
                    self.tr("Import Failed"),
                    self.tr("No valid proxies found."),
                    QtWidgets.QMessageBox.StandardButton.Ok
                )
                return

            self._valid_proxies = valid_proxies
            self.accept()

        except ValidationError as e:
            QtWidgets.QMessageBox.warning(
                self,
                self.tr("Import Failed"),
                str(e),
                QtWidgets.QMessageBox.StandardButton.Ok
            )
        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self,
                self.tr("Import Failed"),
                str(e),
                QtWidgets.QMessageBox.StandardButton.Ok
            )

    def get_valid_proxies(self) -> list[ValidatedProxy]:
        """获取验证通过的代理列表"""
        return self._valid_proxies

    def get_content(self) -> str:
        """获取文本编辑器内容"""
        return self._txt_editor.toPlainText()

    def set_content(self, content: str) -> None:
        """设置文本编辑器内容"""
        self._txt_editor.setPlainText(content)

    @staticmethod
    def export_proxies_to_file(
        parent: QtWidgets.QWidget,
        proxies: Sequence[Sequence[object]],
    ) -> bool:
        """导出代理到文件

        Args:
            proxies: 代理列表，每项为 [name, address, port, type, user, password]

        Returns:
            是否成功导出
        """
        file_name, _ = QtWidgets.QFileDialog.getSaveFileName(
            parent,
            QtCore.QCoreApplication.translate("BatchImportDialog", "Export Proxies"),
            "proxies.txt",
            QtCore.QCoreApplication.translate(
                "BatchImportDialog", "Text Files (*.txt);;All Files (*)"
            ),
        )

        if not file_name:
            return False

        try:
            with open(file_name, "w", encoding="utf-8") as f:
                for proxy in proxies:
                    if len(proxy) < 4:
                        continue
                    name = str(proxy[0])
                    address = str(proxy[1])
                    port = str(proxy[2])
                    ptype = str(proxy[3]) if len(proxy) > 3 else "HTTP"
                    user = str(proxy[4]) if len(proxy) > 4 else ""
                    pwd = str(proxy[5]) if len(proxy) > 5 else ""

                    f.write(format_proxy((name, address, port, ptype, user, pwd)) + "\n")

            QtWidgets.QMessageBox.information(
                parent,
                QtCore.QCoreApplication.translate("BatchImportDialog", "Success"),
                QtCore.QCoreApplication.translate(
                    "BatchImportDialog", "Proxies exported successfully"
                ),
            )
            return True

        except Exception as e:
            failed_message = QtCore.QCoreApplication.translate(
                "BatchImportDialog", "Failed to export proxies"
            )
            QtWidgets.QMessageBox.critical(
                parent,
                QtCore.QCoreApplication.translate("BatchImportDialog", "Error"),
                f"{failed_message}: {e}",
            )
            return False
