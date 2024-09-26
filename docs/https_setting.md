# HTTPS 설정 방법

## vite 예시


`server.key`와 `server.crt`는 각각 **SSL 인증서**와 **비밀키**를 의미하며, HTTPS로 웹 서버를 설정할 때 사용됩니다. Vite 개발 서버에서 HTTPS를 설정하려면 SSL 인증서(`.crt`)와 비밀키(`.key`) 파일을 생성하거나 획득해야 합니다. 다음은 SSL 인증서와 키 파일을 설정하는 방법입니다.

### 1. **로컬 개발 환경에서 자가 서명된 SSL 인증서 생성하기**

로컬 개발 환경에서 사용하기 위해 자가 서명된 SSL 인증서를 직접 생성할 수 있습니다. 이 방법은 보안이 필요하지 않은 로컬 개발 용도에 적합합니다.

#### Step 1: OpenSSL 설치
대부분의 Linux 및 macOS 시스템에는 OpenSSL이 기본적으로 설치되어 있습니다. Windows에서는 [OpenSSL](https://slproweb.com/products/Win32OpenSSL.html)을 설치해야 할 수 있습니다.

- **Ubuntu**에서 OpenSSL을 설치하려면:

  ```bash
  sudo apt install openssl
  ```

- **macOS**에서는 Homebrew를 통해 설치할 수 있습니다:

  ```bash
  brew install openssl
  ```

#### Step 2: SSL 인증서 및 비밀키 생성
다음 명령을 사용하여 SSL 인증서(`server.crt`)와 비밀키(`server.key`) 파일을 생성합니다. 이 인증서는 365일 동안 유효한 자가 서명된 인증서를 만듭니다.

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout server.key -out server.crt
```

이 명령을 실행하면 SSL 인증서를 생성하기 위한 몇 가지 정보를 입력해야 합니다:

- **Country Name**: 2자리 국가 코드를 입력합니다. (예: KR)
- **State or Province Name**: 주 또는 도 이름을 입력합니다.
- **Locality Name**: 도시 이름을 입력합니다.
- **Organization Name**: 회사 또는 조직 이름을 입력합니다.
- **Organizational Unit Name**: 부서 이름을 입력합니다.
- **Common Name**: 도메인 이름 또는 IP 주소를 입력합니다. 로컬 개발 환경에서는 `localhost`를 입력할 수 있습니다.
- **Email Address**: 이메일 주소를 입력합니다. (선택 사항)

이 과정을 완료하면 현재 디렉토리에 `server.key`와 `server.crt` 파일이 생성됩니다.

#### Step 3: Vite에서 HTTPS 설정
Vite 개발 서버에서 HTTPS를 활성화하려면 `vite.config.js` 파일을 수정하여 HTTPS 설정을 추가합니다.

```js
import { defineConfig } from 'vite'
import fs from 'fs'

export default defineConfig({
  server: {
    https: {
      key: fs.readFileSync('./path/to/server.key'),
      cert: fs.readFileSync('./path/to/server.crt'),
    },
    host: '0.0.0.0',  // 외부에서 접근할 수 있도록 설정
    port: 5173,        // 원하는 포트를 설정
  },
})
```

이제 Vite 서버는 HTTPS로 실행되며, `https://localhost:5173`로 접속할 수 있습니다.

#### Step 4: 브라우저에서 SSL 경고 해결
자가 서명된 SSL 인증서는 신뢰할 수 있는 인증 기관(CA)에서 발급된 것이 아니므로, 브라우저에서 보안 경고가 나타날 수 있습니다. 이 경우, 개발 환경에서는 경고를 무시하고 진행할 수 있습니다.

- **Chrome**: "고급" 옵션을 클릭한 후 "안전하지 않음으로 이동"을 클릭합니다.
- **Firefox**: "고급"을 클릭한 후 "위험을 감수하고 계속 진행"을 선택합니다.

---

### 2. **Let's Encrypt를 사용한 무료 SSL 인증서 (프로덕션 환경용)**

만약 **프로덕션 환경**에서 실제 사용자들에게 HTTPS로 서비스를 제공해야 한다면, **Let's Encrypt**와 같은 무료 SSL 인증 기관을 사용하여 신뢰할 수 있는 SSL 인증서를 발급받을 수 있습니다.

#### Step 1: Certbot 설치
Let's Encrypt는 **Certbot**을 통해 자동으로 SSL 인증서를 발급하고 갱신할 수 있습니다. Certbot을 설치하려면 다음 명령을 사용합니다.

- **Ubuntu**에서:

  ```bash
  sudo apt install certbot
  ```

- **macOS**에서 Homebrew를 통해:

  ```bash
  brew install certbot
  ```

#### Step 2: 인증서 발급
Certbot을 사용하여 인증서를 발급받습니다. NGINX나 Apache 같은 웹 서버가 이미 실행 중이어야 하며, Certbot이 서버를 통해 도메인 소유권을 확인합니다.

```bash
sudo certbot certonly --standalone -d your-domain.com
```

이 명령은 Let's Encrypt를 통해 SSL 인증서(`fullchain.pem`)와 비밀키(`privkey.pem`)를 발급합니다.

#### Step 3: Vite에서 Let's Encrypt 인증서 설정
Vite 서버를 프로덕션 환경에서 HTTPS로 설정하려면 `vite.config.js` 파일에서 Let's Encrypt 인증서를 사용하도록 설정할 수 있습니다.

```js
import { defineConfig } from 'vite'
import fs from 'fs'

export default defineConfig({
  server: {
    https: {
      key: fs.readFileSync('/etc/letsencrypt/live/your-domain.com/privkey.pem'),
      cert: fs.readFileSync('/etc/letsencrypt/live/your-domain.com/fullchain.pem'),
    },
    host: 'your-domain.com',  // 도메인 사용
    port: 443,                 // HTTPS 기본 포트
  },
})
```

이 설정을 통해 Vite 서버가 Let's Encrypt로 발급받은 SSL 인증서를 사용하여 HTTPS로 동작하게 됩니다.

---

### 3. **기존 SSL 인증서 사용하기**
만약 이미 상용 인증 기관(CA)으로부터 SSL 인증서를 발급받았다면, 해당 인증서와 키 파일을 Vite 서버에서 사용할 수 있습니다.

- SSL 인증서(`server.crt`)와 키 파일(`server.key`)을 서버에 저장합니다.
- Vite의 `vite.config.js` 파일을 수정하여 해당 파일들을 참조하도록 설정합니다.

```js
import { defineConfig } from 'vite'
import fs from 'fs'

export default defineConfig({
  server: {
    https: {
      key: fs.readFileSync('/path/to/your/server.key'),
      cert: fs.readFileSync('/path/to/your/server.crt'),
    },
    host: '0.0.0.0',  // 외부 접속 허용
    port: 5173,        // 포트 설정
  },
})
```

---

### 결론

1. **로컬 개발**: 자가 서명된 인증서를 생성하여 로컬 개발 환경에서 HTTPS를 설정할 수 있습니다. OpenSSL을 사용하여 `.crt`와 `.key` 파일을 생성한 후 Vite 서버에 적용합니다.
2. **프로덕션 환경**: Let's Encrypt를 사용하여 무료로 SSL 인증서를 발급받을 수 있으며, 이를 Vite 서버에 적용할 수 있습니다.
3. **기존 SSL 인증서**: 상용 SSL 인증서를 이미 보유한 경우 해당 인증서를 그대로 사용할 수 있습니다.

이 설정을 통해 HTTPS를 사용하여 Vite 개발 서버나 프로덕션 환경에서 안전하게 서비스를 제공할 수 있습니다.