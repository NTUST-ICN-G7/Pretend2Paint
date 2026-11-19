"""應用程式進入點（composition root）。

這裡負責把 p2p / streaming / core / ui 組裝起來並啟動。
它不屬於任何一層，因此可以 import 所有模組；其他模組之間的依賴請遵守
docs/architecture.md 的分層規則。
"""


def main() -> None:
    # TODO: 各模組 API 完成後，在這裡組裝並啟動遊戲。
    print("Pretend2Paint: not implemented yet.")


if __name__ == "__main__":
    main()
