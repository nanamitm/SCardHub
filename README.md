すでにアクセスできなくなっているSCardHubのミラーです  
以下、オリジナル  

# Smart Card API Hub for DTV apps. #

DTVアプリ用の特殊なスマートカードリーダとシステム標準のスマートカードリーダを共存させ、  
扱いやすいようにするためのWinSCard.dllハブです。

スマートカードリーダ或いはそれを模したDLLに対応しています。

## 導入 ##

* WinSCard.dll (SCardHub)

	DTVアプリケーションのexeと同じフォルダに配置してください。

* SCardHub.ini

	設定は`SCardHub.ini`に記述します。通常は`WinSCard.dll`と同じフォルダに配置して使います。  
	詳細はサンプルの`SCardHub.ini`に書いてあるコメントを参照してください。

## ビルド環境 ##

### カード状態と ATR の転送

TvCas モジュールの切り替え後も内蔵リーダーを利用できるよう、最初の
`SCardEstablishContext` 呼び出しで Hub をプロセス終了まで保持します。
Hub が途中でアンロードされると、次の TvCas が既にロード済みの System32 の
`WinSCard.dll` に結び付き、内蔵リーダーの一覧が空になる場合があります。
DLL の更新を反映するには、利用中のアプリケーションの終了と再起動が必要です。

配下のカードリーダー DLL が `SCardStatusA` と `SCardGetStatusChangeA` を提供する場合、
Hub の ANSI / Unicode API はその DLL から取得したカード状態と ATR を返します。
これにより、スカパー！プレミアムサービスのカードにも実際の ATR が渡ります。
状態取得時の下位 DLL のエラーも呼び出し元へ返ります。
各 API を提供しない旧式 DLL については、従来の B-CAS 用互換値が使われます。

x64 Release ビルド後、Visual Studio と 64bit Python のある環境では、次のコマンドで
実カードを使わずに状態転送と旧式 DLL 互換を検証できます。
`ScratchDirectory` にはテスト生成物を置く作業用フォルダーを指定します。

```powershell
.\tests\run_status_proxy_test.ps1 -ScratchDirectory C:\Temp\SCardHub-status-test
```

このテストは A/W API、B-CAS とプレミアムの ATR、必要長の問い合わせ、短いバッファ、
自動メモリ確保、カード未挿入、状態変化、下位エラーの伝播を確認します。

実機での切り替え確認には `tests/tvcas_switch_test.py` を使えます。
TVTest フォルダー、B-CAS リーダー名、プレミアム用リーダー名の順に引数を渡すと、
Hub を事前ロードせずに B25 と B1 を交互にロード・解放し、呼び出し先が Hub のままか、
両方の実カードを開けるかを3往復確認します。実行には両方の `.tvcas` が必要です。

以下のコンパイラでビルド可能を確認しています。

* Microsoft Visual C++ 2015 Version 14.0.25425.01 Update 3
* x86_64-w64-mingw32-gcc (GCC) 4.9.2
* i686-w64-mingw32-gcc (GCC) 4.9.2

## ライセンス ##

The MIT License (MIT)

Copyright (c) 2015 jd2015

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

