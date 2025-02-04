# from PDF

PDFファイルをScrapboxで使いやすい形式に変換するツールです。PDFを画像に変換し、Gyazoにアップロードして、OCRでテキストを抽出し、Scrapboxのページとして整形します。

日本語の詳細な説明は[こちら](https://scrapbox.io/nishio/PDF%E3%81%8B%E3%82%89Scrapbox%E3%81%B8)をご覧ください。

## 主な機能

- PDFを画像（JPEGまたはPNG）に変換
- 画像をGyazoにアップロード
- GyazoのOCR機能を使用してテキストを抽出
- 抽出したテキストとGyazoの画像URLをScrapboxのJSON形式に変換
- 1ページあたり10,000行の制限に対応するための自動ページ分割

## インストール

1. 必要なパッケージのインストール:
```bash
pip install -r requirements.txt
```

2. PDFから画像への変換に`pdftocairo`コマンドを使用します。以下のようにインストールしてください：

- macOS: `brew install poppler`
- Ubuntu: `apt-get install poppler-utils`

3. `.env`ファイルを作成し、Gyazoのアクセストークンを設定:
```
GYAZO_TOKEN=your_gyazo_access_token
```

## 使用方法

### 基本的な使用方法

```bash
python main.py --in-file input.pdf
```

または、ディレクトリ内の全PDFを処理:

```bash
python main.py --in-dir input_directory
```

### コマンドライン引数

- `--in-file`, `--in`, `-i`: 入力PDFファイル
- `--resolution`, `-r`: 出力画像の解像度（デフォルト: 200）
- `--format`, `-f`: 出力画像フォーマット（jpeg/png、デフォルト: jpeg）
- `--in-dir`: 入力PDFディレクトリ（デフォルト: in）
- `--out-dir`: 出力ディレクトリ（デフォルト: out）
- `--retry`: エラー時に再試行
- `--skip-gyazo`: GyazoアップロードとOCRをスキップ
- `--skip-gyazo-upload`: Gyazoアップロードのみスキップ
- `--skip-pdf-to-image`: PDF→画像変換をスキップ
- `--recovery`: 429エラー（リクエスト制限）後の復旧モード
- `--filter`: 処理済みPDFのフィルタリング

### 出力ディレクトリ構造

```
out/
  └── pdf_name/
      ├── page-*.jpg        # 変換された画像ファイル
      ├── gyazo_info.json   # Gyazoアップロード情報
      └── scrapbox.json     # Scrapbox用JSON
```

## 依存関係

- python-dotenv: 環境変数の管理
- requests: HTTPリクエスト
- tqdm: プログレスバーの表示
- pdftocairo: PDFから画像への変換（外部コマンド）

## 注意事項

- Gyazo APIには1日あたりのリクエスト制限（12,500回）があります
- Scrapboxの1ページあたりの行数制限（10,000行）に対応するため、長いPDFは自動的に複数ページに分割されます
- PDFがDropboxにある場合、オフラインモードでないとPDF変換でエラーが発生する可能性があります