<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Password Protected</title>
</head>
<body>
    <h1>Enter Password</h1>

    <form action="{{ route('password.check') }}" method="POST">
        @csrf
        <input type="password" name="password" placeholder="Enter password" required>
        <button type="submit">Submit</button>
    </form>

    @if ($errors->any())
        <div>
            <strong>{{ $errors->first('password') }}</strong>
        </div>
    @endif
</body>
</html>