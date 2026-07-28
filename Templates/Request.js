let awaiting_response = false;

async function post_request(url, data) {
	if (awaiting_response) {
		return null;
	}
	awaiting_response = true;
	const ret = await fetch(url, {
  method: "POST",
  body: JSON.stringify(data),
  headers: {
    "Content-type": "application/json; charset=UTF-8"
  }
});
	awaiting_response = false;
return ret;
}

async function patch_request(url, data) {
	if (awaiting_response) {
		return null;
	}
	awaiting_response = true;
	const ret = await fetch(url, {
  method: "PATCH",
  body: JSON.stringify(data),
  headers: {
    "Content-type": "application/json; charset=UTF-8"
  }
});
	awaiting_response = false;
return ret;
}