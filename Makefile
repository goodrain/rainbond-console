PRE-COMMIT-FILE = .git/hooks/pre-commit
init: 
	test -s $(PRE-COMMIT-FILE) || cp .githook/pre-commit $(PRE-COMMIT-FILE)
format:
	@yapf --exclude env --exclude venv --exclude static --exclude www/alipay_direct --exclude www/utils/mnssdk --exclude backends --style style.cfg  -r ./ -i
check:
	@flake8 --exclude venv,env,static,www/alipay_direct,www/utils/mnssdk,backends,migrations --extend-ignore=W605 --max-line-length 129 ./
build-base:
	docker build -t rainbond/rbd-ui-base:V5.3 -f Dockerfile.base .
build-allinone-image:
	docker build -t --tag VERSION=V5.3 --tag rainbond/rainbond:v5.3 -f Dockerfile.allinone .	