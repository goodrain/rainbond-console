PRE-COMMIT-FILE = .git/hooks/pre-commit
init: 
	test -s $(PRE-COMMIT-FILE) || cp .githook/pre-commit $(PRE-COMMIT-FILE)
format:
	@yapf --exclude env --exclude venv --exclude static --exclude www/alipay_direct --exclude www/utils/mnssdk --exclude backends --style style.cfg  -r ./ -i
check:
	@flake8 --exclude env,static,www/alipay_direct,www/utils/mnssdk,backends --extend-ignore=W605 --max-line-length 129 ./
