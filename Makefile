PRE-COMMIT-FILE = .git/hooks/pre-commit
init: 
	test -s $(PRE-COMMIT-FILE) || cp .githook/pre-commit $(PRE-COMMIT-FILE)
format:
	@yapf --exclude env --exclude static --style style.cfg  -r ./ -i
check: init format
	@flake8 --exclude env,static,www/alipay_direct,www/utils/mnssdk,backends --extend-ignore=W605 --max-line-length 129 ./
